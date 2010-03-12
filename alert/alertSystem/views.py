# This software and any associated files are copyright 2010 Brian Carver and
# Michael Lissner.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from alert.alertSystem.models import *
from alert.alertSystem.titlecase import titlecase
from django.http import HttpResponse, Http404
from django.core.files import File
from django.core.files.base import ContentFile
import datetime, hashlib, re, StringIO, urllib, urllib2
from BeautifulSoup import BeautifulSoup
from lxml.html import fromstring
from lxml import etree




def downloadPDF(LinkToPdf, caseNameShort):
    """Receive a URL and a casename as an argument, then downloads the PDF
    that's in it, and places it intelligently into the database. Can accept
    either relative or absolute URLs

    returns a StringIO that is the PDF, I think
    """


    webFile = urllib2.urlopen(LinkToPdf)

    stringThing = StringIO.StringIO()
    stringThing.write(webFile.read())

    myFile = ContentFile(stringThing.getvalue())

    webFile.close()
    return myFile


def make_url_absolute(url, rel_url):
    """give it a URL and a URL you suspect to be a relative one. It'll strip the
    domain name out of the first URL, and, if needed, attach it to the suspected
    rel_url.

    returns an absolute version of rel_url
    """
    if 'http:' not in rel_url:
        #it's a relative url, fix it.
        rel_url = url.split('/')[0] + "//" + url.split('/')[2] + rel_url
    return rel_url


def hasDuplicate(caseNumber, caseNameShort):
    """give it a caseNumber and a caseNameShort, and it'll tell you if that is
    already in the DB"""

    try:
        Citation.objects.get(caseNumber = caseNumber, caseNameShort =
            caseNameShort)
        print "duplicate found!"
        hasDup = True
    except:
        hasDup = False
    return hasDup


def scrape(request, courtID):
    """
    The master function. This will receive a court ID, determine the correct
    action to take (scrape for PDFs, download content, etc.), then hand it off
    to another function that will handle the nitty-gritty crud.

    returns None
    """

    # some data validation, for good measure - this should already be done via
    # our url regex
    try:
        courtID = int(courtID)
    except:
        raise Http404()

    # next, we attack the court requested.
    if (courtID == 1):
        """
        first circuit doesn't actually do PDFs. They do links to HTML content.
        From what I can tell, this content is generated with pdftohtml. The
        process for this court is therefore as follows:
        1. visit the site
        2. follow the links on the site
        3. download the html, parsing it for text.
        """
        url = "http://www.ca1.uscourts.gov/cgi-bin/newopn.pl"

        html = urllib2.urlopen(url)
        soup = BeautifulSoup(html)

        tdTags = soup.findAll('td')

        ct = Court.objects.get(courtUUID='ca1')

        i = 0
        while i < len(tdTags)-4:
            # some beautiful soup work here...
            caseDate = tdTags[i+1].contents[0].strip().strip('&nbsp;')
            caseLink = tdTags[i+2].contents[0].get('href')
            caseNumber = tdTags[i+3].contents[1].contents[0].strip()\
                .strip('&nbsp;')
            caseNameShort = tdTags[i+4].contents[0].strip().strip('&nbsp;')

            doc = Document()

            # great, now we do some parsing and building, beginning with the
            # caseLink
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can download the cases
            fileHandle = urllib2.urlopen(caseLink)
            html = fileHandle.read()
            doc.documentPlainText = html
            fileHandle.close()

            # and using the case text, we can generate our sha1 hash
            sha1Hash = hashlib.sha1(html).hexdigest()
            doc.documentSHA1 = sha1Hash


            # next up is the caseDate
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[2]), int(splitDate[0]), 
                int(splitDate[1]))
            doc.dateFiled = caseDate


            # next, we do caseNumber and caseNameShort
            cite = Citation()
            cite.caseNumber = caseNumber
            cite.caseNameShort = caseNameShort

            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # and finally, we link up the foreign keys and save the data
            doc.court = ct
            cite.save()
            doc.citation = cite
            doc.save()

            # increment our while loop counter, i, by the number of columns in
            # the table
            i = i + 4



    elif (courtID == 2):
        # second circuit
        url = "http://www.ca2.uscourts.gov/decisions"
        ct = Court.objects.get(courtUUID='ca2')

        """
        queries can be made on their system via HTTP POST, but I can't figure out
        how to URL hack it. I've made a request for help (2010-03-06)
        http://www.ca2.uscourts.gov/decisions?IW_DATABASE=OPN&IW_FIELD_TEXT=OPN&IW_SORT=-Date&IW_BATCHSIZE=25
        """

    elif (courtID == 3):
        """
        This URL provides the latest 25 cases, so I need to pick out the new
        ones and only get those. I can do this efficiently by trying to do each,
        and then giving up once I hit one that I've done before. This will work
        because they are in reverse chronological order.
        """

        url = "http://www.ca3.uscourts.gov/recentop/week/recprec.htm"
        ct = Court.objects.get(courtUUID='ca3')

        html = urllib2.urlopen(url)
        soup = BeautifulSoup(html)


        # all links ending in pdf, case insensitive
        regex = re.compile("pdf$", re.IGNORECASE)
        aTags = soup.findAll(attrs={"href": regex})

        # we will use these vars in our while loop, better not to compile them
        # each time
        regexII = re.compile('\d{2}/\d{2}/\d{2}')
        regexIII = re.compile('\d{2}-\d{4}')
        i = 0

        while i < len(aTags):
            caseLink = aTags[i].get('href')
            caseNameShort = aTags[i].contents[0].strip().strip('&npsp;')

            junk = aTags[i].previous.previous.previous

            try:
                # this error seems to happen upon dups...not sure why yet
                caseDate = regexII.search(junk).group(0)
                caseNumber = regexIII.search(junk).group(0)
            except:
                i = i+1
                continue

            # these will hold our final document and citation
            doc = Document()
            cite = Citation()

            # link the court early - it helps later
            doc.court = ct

            # next, we do caseNumber and caseNameShort
            cite.caseNumber = caseNumber
            cite.caseNameShort = caseNameShort

            # next, we check for a dup. If there is one, we can break from the
            # loop, since this court posts in alphabetical order.
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                break

            cite.save()
            doc.citation = cite

            # next up is the caseDate
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int("20" + splitDate[2]),int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            # the download URL for the PDF
            caseLink = make_url_absolute(url, caseLink)

            doc.download_URL = caseLink

            # save the file to the db and hard drive
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1

    elif (courtID == 4):
        """Fourth circuit everybody, fourth circuit! Off we go."""

        url = "http://pacer.ca4.uscourts.gov/opinions_today.htm"
        ct = Court.objects.get(courtUUID='ca4')

        html = urllib2.urlopen(url).read()

        # sadly, beautifulsoup chokes on the lines lines of this file because
        # the HTML is so bad. Stop laughing - the HTML IS awful, but it's not
        # funny. Anyway, to make this thing work, we must pull out the target
        # attributes. And so we do.
        regex = re.compile("target.*>", re.IGNORECASE)
        html = re.sub(regex, ">", html)


        soup = BeautifulSoup(html)

        # all links ending in pdf, case insensitive
        regex = re.compile("pdf$", re.IGNORECASE)
        aTags = soup.findAll(attrs={"href": regex})

        i = 0
        regexII = re.compile('\d{2}/\d{2}/\d{4}')
        regexIII = re.compile('\d{4}(.*)')

        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation()

            # link the court early - it helps later
            doc.court = ct

            # next, we'll sort out the caseLink field, and save it
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caselink, we can get the caseNumber and documentType
            fileName = caseLink.split('/')[-1]
            caseNumber, documentType = fileName.split('.')[0:2]

            # next, we do the caseDate and caseNameShort, so we can quit before
            # we get too far along.
            junk = aTags[i].contents[0].strip().strip('&nbsp;')
            try:
                # this error seems to happen upon dups...not sure why yet
                caseDate = regexII.search(junk).group(0).strip()
                caseNameShort = regexIII.search(junk).group(1).strip()
            except:
                i += 1
                continue

            # some caseDate cleanup
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[2]),int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            doc.documentType = documentType
            cite.caseNumber = caseNumber
            cite.caseNameShort = caseNameShort

            # let's check for duplicates before we proceed
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we can save.
            cite.save()
            doc.citation = cite

            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1


    if (courtID == 5):
        """Fifth circuit scraper. Similar process as to elsewhere, as you might
        expect at this point"""

        url = "http://www.ca5.uscourts.gov/Opinions.aspx"
        ct = Court.objects.get(courtUUID='ca5')

        html = urllib2.urlopen(url)
        soup = BeautifulSoup(html)


        #all links ending in pdf, case insensitive
        aTagRegex = re.compile("pdf$", re.IGNORECASE)
        aTags = soup.findAll(attrs={"href": aTagRegex})

        opinionRegex = re.compile(r"\opinions.*pub")
        unpubRegex = re.compile(r"\opinions\unpub")

        i = 0
        while i < len(aTags):
            # this page has PDFs that aren't cases, we must filter them out
            if opinionRegex.search(str(aTags[i])) == None:
                # it's not an opinion, increment and punt
                i += 1
                continue

            # these will hold our final document and citation
            doc = Document()
            cite = Citation()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can get the caseNumber and documentType
            caseNumber = aTags[i].contents[0]
            cite.caseNumber = caseNumber

            if unpubRegex.search(str(aTags[i])) == None:
                # it's published, else it's unpublished
                documentType = "P"
            else:
                documentType = "U"

            doc.documentType = documentType

            # next, we do the caseDate
            caseDate = aTags[i].next.next.contents[0].contents[0]

            # some caseDate cleanup
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[2]),int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            # next, we do the caseNameShort
            caseNameShort = aTags[i].next.next.next.next.next.contents[0]\
                .contents[0].strip().strip('&nbsp;')
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()


            # next
            i += 1


    if (courtID == 6):
        """This one is a pain because their results form doesn't tell you the
        date things were posted. However, if we perform a search by doing a
        POST, we can get a format that has the results. Frustrating, yes, but
        the only other option is parsing the PDFs.

        I called to harass them about this. It didn't help."""

        url = "http://www.ca6.uscourts.gov/cgi-bin/opinions.pl"
        ct = Court.objects.get(courtUUID = 'ca6')

        today = datetime.date.today()
        formattedToday = str(today.month) + '/' + str(today.day) + '/' +\
            str(today.year)

        postValues = {
            'CASENUM' : '',
            'TITLE' : '',
            'FROMDATE' : formattedToday,
            'TODATE' : formattedToday,
            'OPINNUM' : ''
            }

        data = urllib.urlencode(postValues)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        html = response.read()

        soup = BeautifulSoup(html)

        aTagsRegex = re.compile('pdf$', re.IGNORECASE)
        aTags = soup.findAll(attrs={'href' : aTagsRegex})

        i = 0
        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can get the caseNumber and documentType
            caseNumber = aTags[i].contents[0]
            cite.caseNumber = caseNumber

            if 'n' in caseNumber:
                # it's unpublished
                documentType = "U"
            elif 'p' in caseNumber:
                documentType = "P"
            doc.documentType = documentType

            # next, we can do the caseDate
            caseDate = aTags[i].next.next.next.next.next.next.next.next\
                .contents[0].strip().strip('&nbsp;')

            # some caseDate cleanup
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[0]),int(splitDate[1]),
                int(splitDate[2]))
            doc.dateFiled = caseDate

            # next, the caseNameShort (there's probably a better way to do this.
            caseNameShort = aTags[i].next.next.next.next.next.next.next.next\
                .next.next.next.strip().strip('&nbsp;')
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            # next
            i += 1


    if (courtID == 7):
        """another court where we need to do a post. This will be a good
        starting place for getting the judge field, when we're ready for that"""

        url = "http://www.ca7.uscourts.gov/fdocs/docs.fwx"
        ct = Court.objects.get(courtUUID = 'ca7')

        data = "yr=&num=&Submit=Today&dtype=Opinion&scrid=Select+a+Case"
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        html = response.read()

        soup = BeautifulSoup(html)

        aTagsRegex = re.compile('pdf$', re.IGNORECASE)
        aTags = soup.findAll(attrs={'href' : aTagsRegex})

        i = 0
        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation ()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get("href")
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can get the caseNumber and documentType
            caseNumber = aTags[i].previous.previous.previous.previous.previous\
                .previous.previous.previous.previous.previous.strip()
            cite.caseNumber = caseNumber

            # next up: caseDate
            caseDate = aTags[i].previous.previous.previous.contents[0].strip()
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[2]), int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            # next up: caseNameShort
            caseNameShort = aTags[i].previous.previous.previous.previous\
                .previous.previous.previous.strip()
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1

    if (courtID == 8):
        url = "http://www.ca8.uscourts.gov/cgi-bin/new/today2.pl"
        ct = Court.objects.get(courtUUID = 'ca8')

        html = urllib2.urlopen(url)
        soup = BeautifulSoup(html)

        aTagsRegex = re.compile('pdf$', re.IGNORECASE)
        aTags = soup.findAll(attrs={'href' : aTagsRegex})

        caseNumRegex = re.compile('(\d{2})(\d{4})(u|p)', re.IGNORECASE)
        caseDateRegex = re.compile('(\d{2}/\d{2}/\d{4})(.*)(</b>)')
        i = 0
        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation ()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can get the caseNumber and documentType
            junk = aTags[i].contents[0]
            caseNumber = caseNumRegex.search(junk).group(1) + "-" +\
                caseNumRegex.search(junk).group(2)
            documentType = caseNumRegex.search(junk).group(3).upper()

            cite.caseNumber = caseNumber
            doc.documentType = documentType

            # caseDate is next on the block
            junk = str(aTags[i].next.next.next)
            caseDate = caseDateRegex.search(junk).group(1)\
                .strip().strip('&nbsp;')
            caseNameShort = caseDateRegex.search(junk).group(2)\
                .strip().strip('&nbsp;')
            cite.caseNameShort = caseNameShort

            # some caseDate cleanup
            splitDate = caseDate.split('/')
            caseDate = datetime.date(int(splitDate[2]),int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1

    if (courtID == 9):
        """This court, by virtue of having a javascript laden website, was very
        hard to parse properly. BeautifulSoup couldn't handle it at all, so lxml
        has to be used. lxml seems pretty useful, but it was a pain to learn."""

        url = "http://www.ca9.uscourts.gov/opinions/?o_mode=view" +\
              "&amp;o_sort_field=24&amp;o_sort_field_by=19&amp;o_sort_type=" +\
              "asc&o_page_size=10"

        ct = Court.objects.get(courtUUID = 'ca9')

        req = urllib2.urlopen(url).read()
        tree = fromstring(req)

        caseLinks = tree.xpath('//table[3]/tbody/tr/td/a')
        caseNumbers = tree.xpath('//table[3]/tbody/tr/td[2]/label')
        caseDates = tree.xpath('//table[3]/tbody/tr/td[6]/label')

        i = 0
        while i < len(caseLinks):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation ()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = caseLinks[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # next, we'll do the caseNumber
            caseNumber = caseNumbers[i].text
            cite.caseNumber = caseNumber

            # next up: document type (static for now)
            doc.documentType = "P"

            # next up: caseDate
            splitDate = caseDates[i].text.split('/')
            caseDate = datetime.date(int(splitDate[2]), int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            #next up: caseNameShort
            caseNameShort = titlecase(caseLinks[i].text.lower())
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue


            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1

    elif (courtID == 10):
        url = "http://www.ck10.uscourts.gov/searchbydateresults.php"
        ct = Court.objects.get(courtUUID = 'ca10')

        today = datetime.date.today()
        formattedToday = str(today.month) + "%2F" + str(today.day) + "%2F" +\
            str(today.year)
        data = "begin=" + formattedToday + "&end=" + formattedToday +\
            "&Date=Search"

        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        html = response.read()

        soup = BeautifulSoup(html)
        print soup
        aTagsRegex = re.compile('\d{3}.pdf$', re.IGNORECASE)
        aTags = soup.findAll(attrs={'href' : aTagsRegex})

        caseNumRegex = re.compile('\d{2}-\d{4}', re.IGNORECASE)

        i = 0
        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink
            print caseLink


            # using caseLink, we can get the caseNumber
            caseNumber = caseNumRegex.search(caseLink).group(0)\
                .strip().strip('&nbsp;')
            cite.caseNumber = caseNumber
            print caseNumber

            # next up: caseDate. dateFiled == today because of the query we
            # began with.
            caseDate = datetime.date.today()
            doc.dateFiled = caseDate

            # next, the caseNameShort
            try:
                # this is in a try block because occasionally, there are pdfs
                # that we don't want. Those will throw errors here, and we'll
                # move on in that case.
                caseNameShort = aTags[i].next.next.next.strip().strip('&nbsp;')
            except:
                i += 1
                continue

            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            # next
            i += 1
            
    elif (courtID == 11):
        """Trying out an RSS feed this time, since the feed looks good."""
        url = "http://www.ca11.uscourts.gov/rss/pubopnsfeed.php"
        
        ct = Court.objects.get(courtUUID = 'ca11')

        req = urllib2.urlopen(url)
        tree = etree.parse(req)

        caseLinks = tree.xpath('//item/link')
        description = tree.xpath('//item/description')
        caseNames = tree.xpath('//item/title')
        
        # some regexes
        caseNumRegex = re.compile('''
            case            # the word case
            .*?             # some junk, not greedy
            (\d{2}-\d{5})   # two digits a hyphen then five more
            ''', re.IGNORECASE | re.VERBOSE)
        
        caseDateRegex = re.compile('''
            date                    # the word date
            .*?                     # some junk, not greedy
            (\d{2}-\d{2}-\d{4})     # two digits - two digits - four digits
            ''', re.IGNORECASE | re.VERBOSE)       
        
        i = 0
        while i < len(caseLinks):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation ()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = caseLinks[i].text
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink
            
            # these are only published opinions
            doc.documentType = "P"
            
            # next, we'll do the caseNumber
            caseNumber = caseNumRegex.search(description[i].text).group(1)
            cite.caseNumber = caseNumber
            
            # next up: caseDate
            caseDate = caseDateRegex.search(description[i].text).group(1)
            splitDate = caseDate.split('-')
            caseDate = datetime.date(int(splitDate[2]), int(splitDate[0]),
                int(splitDate[1]))
            doc.dateFiled = caseDate

            #next up: caseNameShort
            caseNameShort = caseNames[i].text.strip().strip('&nbsp;')
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue


            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()

            i += 1
    
    if (courtID == 12):
        url = "http://www.cadc.uscourts.gov/bin/opinions/allopinions.asp"
        ct = Court.objects.get(courtUUID = 'cadc')
        
        html = urllib2.urlopen(url)
        soup = BeautifulSoup(html)
        
        aTagsRegex = re.compile('pdf$', re.IGNORECASE)
        aTags = soup.findAll(attrs={'href' : aTagsRegex})
        
        caseNumRegex = re.compile("(\d{2}-\d{4})") 
        

        i = 0
        while i < len(aTags):
            # these will hold our final document and citation
            doc = Document()
            cite = Citation ()

            # link the court early - it helps later
            doc.court = ct

            # we begin with the caseLink field
            caseLink = aTags[i].get('href')
            caseLink = make_url_absolute(url, caseLink)
            doc.download_URL = caseLink

            # using caseLink, we can get the caseNumber and documentType
            caseNumber =  caseNumRegex.search(caseLink).group(1)
            cite.caseNumber = caseNumber
            
            # we can hard-code this b/c the D.C. Court paywalls all
            # unpublished opinions.
            doc.documentType = "P"

            # caseDate is next on the block
            caseDate = datetime.date.today()
            doc.dateFiled = caseDate
            
            caseNameShort = aTags[i].next.next.next.strip().strip('&nbsp;')
            cite.caseNameShort = caseNameShort

            # now that we have the caseNumber and caseNameShort, we can dup check
            dup = hasDuplicate(caseNumber, caseNameShort)
            if dup:
                i += 1
                continue

            # if that goes well, we save to the DB
            cite.save()
            doc.citation = cite

            # finally, we can download the PDFs and save them locally
            # finally, we should download the PDF and save it locally.
            myFile = downloadPDF(caseLink, caseNameShort)
            doc.local_path.save(caseNameShort + ".pdf", myFile)

            # and using the PDF we just downloaded, we can generate our sha1 hash
            data = doc.local_path.read()
            sha1Hash = hashlib.sha1(data).hexdigest()
            doc.documentSHA1 = sha1Hash

            # finalize everything
            doc.save()
            
            i += 1        
        
        
    """

    ...etc for each

    """


    return HttpResponse("it worked")
