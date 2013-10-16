from collections import OrderedDict
from lxml import html
import os
from lxml.html import tostring

os.environ['DJANGO_SETTINGS_MODULE'] = 'alert.settings'

import sys
execfile('/etc/courtlistener')
sys.path.append(INSTALL_ROOT)

from django import db
from django.conf import settings
from alert.search.models import Document
from alert.lib import sunburnt
from alert.lib.encode_decode import num_to_ascii
from cleaning_scripts.lib.string_diff import find_confidences, gen_diff_ratio
import datetime
from datetime import date
import re

DEBUG = True


def build_date_range(date_filed, range=5):
    """Build a date range to be handed off to a solr query

    """
    after = date_filed - datetime.timedelta(days=range)
    before = date_filed + datetime.timedelta(days=range + 1)
    date_range = '[%sZ TO %sZ]' % (after.isoformat(),
                                   before.isoformat())
    return date_range


def load_stopwords():
    """Loads Sphinx's stopwords file.

    Pulls in the top 5000 words as generated by Sphinx, and returns them as
    an array.
    """
    stopwords = []
    with open('%s/alert/corpus_importer/word_freq.5000.txt' % INSTALL_ROOT, 'r') as stopwords_file:
        for word in stopwords_file:
            stopwords.append(word.strip().decode('utf-8'))
    return stopwords
stopwords = load_stopwords()  # Module-level.


def get_good_words(word_list, stop_words_size=500):
    """Cleans out stop words, abbreviations, etc. from a list of words"""
    good_words = []
    for word in word_list:
        # Clean things up
        word = re.sub(r"'s", '', word)
        word = word.strip('*,();"')

        # Boolean conditions
        stop = word in stopwords[:stop_words_size]
        bad_stuff = re.search('[0-9./()!:&\']', word)
        too_short = (len(word) <= 1)
        is_acronym = (word.isupper() and len(word) <= 3)
        if any([stop, bad_stuff, too_short, is_acronym]):
            continue
        else:
            good_words.append(word)
    # Eliminate dups, but keep order.
    return list(OrderedDict.fromkeys(good_words))


def make_case_name_solr_query(caseName, court, date_filed, DEBUG=False):
    """Grab words from the content and returns them to the caller.

    This function attempts to choose words from the content that would return
    the fewest cases if queried. Words are selected from the case name and the
    content.
    """
    main_params = {
        'fq': [
            'court_exact:%s' % court,
            'dateFiled:%s' % build_date_range(date_filed, range=15)
        ],
        'rows': 100
    }

    case_name_q_words = []
    case_name_words = caseName.split()
    if ' v. ' in caseName.lower():
        v_index = case_name_words.index('v.')
        # The first word of the defendant and the last word in the plaintiff that's
        # not a bad word.
        plaintiff_a = get_good_words(case_name_words[:v_index])
        defendant_a = get_good_words(case_name_words[v_index + 1:])
        if plaintiff_a:
            case_name_q_words.append(plaintiff_a[-1])
        if defendant_a:
            # append the first good word that's not already in the array
            try:
                case_name_q_words.append([word for word in defendant_a if word not in case_name_q_words][0])
            except IndexError:
                # When no good words left in defendant_a
                pass
    elif 'in re ' in caseName.lower() or 'matter of ' in caseName.lower() or 'ex parte' in caseName.lower():
        try:
            subject = re.search('(?:(?:in re)|(?:matter of)|(?:ex parte)) (.*)', caseName, re.I).group(1)
        except TypeError:
            subject = ''
        good_words = get_good_words(subject.split())
        if good_words:
            case_name_q_words.append(good_words[0])
    else:
        case_name_q_words = get_good_words(caseName.split())
    if case_name_q_words:
        main_params['fq'].append('caseName:(%s)' % ' '.join(case_name_q_words))

    return main_params


def get_dup_stats(doc):
    """The heart of the duplicate algorithm. Returns stats about the case as
    compared to other cases already in the system. Other methods can call this
    one, and can make decisions based on the stats generated here.

    If no likely duplicates are encountered, stats are returned as zeroes.

    Process:
        1. Refine the possible result set down to just a few candidates.
        2. Determine their likelihood of being duplicates according to a
           number of measures:
            - Similarity of case name
            - Similarity of docket number
            - Comparison of content length
    """
    conn = sunburnt.SolrInterface(settings.SOLR_URL, mode='r')
    stats = []
    DEBUG = True

    ##########################################
    # 1: Refine by date, court and case name #
    ##########################################
    main_params = make_case_name_solr_query(
        doc.citation.case_name,
        doc.court_id,
        doc.date_filed,
        DEBUG=DEBUG,
    )
    if DEBUG:
        print "    - main_params are: %s" % main_params
    candidates = conn.raw_query(**main_params).execute()

    if not len(candidates) and doc.citation.docket_number is not None:
        # Try by docket number rather than case name
        docket_q = ' OR '.join([w.strip('*,();"') for w in doc.citation.docket_number.split()
                                if re.search('\d', w)])
        if docket_q:
            main_params = {
                'fq': [
                    'court_exact:%s' % doc.court_id,
                    'dateFiled:%s' % build_date_range(doc.date_filed, range=15),
                    'docketNumber:(%s)' % docket_q
                ],
                'rows': 100
            }
            if DEBUG:
                print "    - main_params are: %s" % main_params
            candidates = conn.raw_query(**main_params).execute()

    if not len(candidates) and doc.court_id == 'scotus':
        if doc.citation.federal_cite_one:
            # Scotus case, try by citation.
            main_params = {
                'fq': [
                    'court_exact:%s' % doc.court_id,
                    'dateFiled:%s' % build_date_range(doc.date_filed, range=90),  # Creates ~6 month span.
                    'citation:(%s)' % ' '.join([re.sub(r"\D", '', w) for w in doc.citation.federal_cite_one.split()])
                ],
                'rows': 100,
            }
            if DEBUG:
                print "    - main_params are: %s" % main_params
            candidates = conn.raw_query(**main_params).execute()

    stats.append(len(candidates))
    if not len(candidates):
        return stats, candidates

    #########################################
    # 2: Attempt filtering by docket number #
    #########################################
    # Two-step process. First we see if we have any exact hits.
    # Second, if there were exact hits, we forward those onwards. If not, we
    # forward everything.
    remaining_candidates = []
    if doc.citation.docket_number:
        new_docket_number = re.sub("(\D|0)", "", doc.citation.docket_number)
        for candidate in candidates:
            if candidate.get('docketNumber'):
                # Get rid of anything in the docket numbers that's not a digit
                result_docket_number = re.sub("(\D|0)", "", candidate['docketNumber'])
                # Get rid of zeroes too.
                if new_docket_number == result_docket_number:
                    remaining_candidates.append(candidate)

    if len(remaining_candidates) > 0:
        # We had one or more exact hits! Use those.
        candidates = remaining_candidates
    else:
        # We just let candidates from step one get passed through by doing nothing.
        pass
    stats.append(len(candidates))

    ##############################
    # 3: Find the best case name #
    ##############################
    confidences = find_confidences(candidates, doc.citation.case_name)
    stats.append(confidences)

    ###########################
    # 4: Check content length #
    ###########################
    percent_diffs, gestalt_diffs = [], []
    new_stripped_content = re.sub('\W', '', doc.body_text).lower()
    for candidate in candidates:
        candidate_stripped_content = re.sub('\W', '', candidate['text']).lower()

        # Calculate the difference in text length and their gestalt difference
        length_diff = abs(len(candidate_stripped_content) - len(new_stripped_content))
        percent_diff = float(length_diff) / len(new_stripped_content)
        percent_diffs.append(percent_diff)
        gestalt_diffs.append(gen_diff_ratio(candidate_stripped_content, new_stripped_content))

    stats.append(percent_diffs)
    stats.append(gestalt_diffs)

    return stats, candidates


def write_dups(source, dups, DEBUG=False):
    """Writes duplicates to a file so they are logged.

    This function receives a queryset and then writes out the values to a log.
    """
    log = open('dup_log.txt', 'a')
    if dups[0] is not None:
        log.write(str(source.pk))
        print "  Logging match: " + str(source.pk),
        for dup in dups:
            # write out each doc
            log.write('|' + str(dup.pk) + " - " + num_to_ascii(dup.pk))
            if DEBUG:
                print '|' + str(dup.pk) + ' - ' + num_to_ascii(dup.pk),
    else:
        log.write("  No dups found for %s" % source.pk)
        if DEBUG:
            print "  No dups found for %s" % source.pk
    print ''
    log.write('\n')
    log.close()


def import_and_report_records():
    """Traverses the first 500 records and find their dups.

    This script is used to find dups within the database by comparing it to
    the Sphinx index. This simulates the duplicate detection we will need to
    do when importing from other sources, and allows us to test it.
    """

    docs = Document.objects.filter(court='ca1')[:5000]
    #docs = Document.objects.filter(pk = 985184)

    # do this 1000 times
    for doc in docs:
        court = doc.court_id
        date = doc.date_filed
        casename = doc.citation.caseNameFull
        docket_number = doc.citation.docket_number
        content = doc.plain_text
        id = num_to_ascii(doc.pk)
        if content == "":
            # HTML content!
            content = doc.html
            br = re.compile(r'<br/?>')
            content = br.sub(' ', content)
            p = re.compile(r'<.*?>')
            content = p.sub('', content)

        dups = check_dup(court, date, casename, content, docket_number, id, True)

        if len(dups) > 0:
            # duplicate(s) were found, write them out to a log
            write_dups(doc, dups, True)

        if DEBUG:
            print ''
        # Clear query cache, as it presents a memory leak when in dev mode
        db.reset_queries()

    return


def main():
    print import_and_report_records()
    print "Completed 500 records successfully. Exiting."
    exit(0)


if __name__ == '__main__':
    main()

