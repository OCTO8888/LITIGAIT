# -*- coding: utf-8 -*-
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
#
#  Under Sections 7(a) and 7(b) of version 3 of the GNU Affero General Public
#  License, that license is supplemented by the following terms:
#
#  a) You are required to preserve this legal notice and all author
#  attributions in this program and its accompanying documentation.
#
#  b) You are prohibited from misrepresenting the origin of any material
#  within this covered work and you are required to mark in reasonable
#  ways how any modified versions differ from the original version.
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'Tag'
        db.delete_table('Tag')

        # Changing field 'Alert.sendNegativeAlert'
        db.alter_column('Alert', 'sendNegativeAlert', self.gf('django.db.models.fields.BooleanField')(blank=True))

        # Changing field 'Alert.alertPrivacy'
        db.alter_column('Alert', 'alertPrivacy', self.gf('django.db.models.fields.BooleanField')(blank=True))

        # Deleting field 'Favorite.user'
        db.delete_column('Favorite', 'user_id')

        # Adding field 'Favorite.name'
        db.add_column('Favorite', 'name', self.gf('django.db.models.fields.TextField')(default=' ', max_length=200), keep_default=False)

        # Removing M2M table for field tags on 'Favorite'
        db.delete_table('Favorite_tags')

        # Changing field 'UserProfile.plaintextPreferred'
        db.alter_column('UserProfile', 'plaintextPreferred', self.gf('django.db.models.fields.BooleanField')(blank=True))

        # Changing field 'UserProfile.wantsNewsletter'
        db.alter_column('UserProfile', 'wantsNewsletter', self.gf('django.db.models.fields.BooleanField')(blank=True))

        # Changing field 'UserProfile.emailConfirmed'
        db.alter_column('UserProfile', 'emailConfirmed', self.gf('django.db.models.fields.BooleanField')(blank=True))


    def backwards(self, orm):
        
        # Adding model 'Tag'
        db.create_table('Tag', (
            ('tag', self.gf('django.db.models.fields.CharField')(max_length=30, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('userHandling', ['Tag'])

        # Changing field 'Alert.sendNegativeAlert'
        db.alter_column('Alert', 'sendNegativeAlert', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'Alert.alertPrivacy'
        db.alter_column('Alert', 'alertPrivacy', self.gf('django.db.models.fields.BooleanField')())

        # Adding field 'Favorite.user'
        db.add_column('Favorite', 'user', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['auth.User']), keep_default=False)

        # Deleting field 'Favorite.name'
        db.delete_column('Favorite', 'name')

        # Adding M2M table for field tags on 'Favorite'
        db.create_table('Favorite_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('favorite', models.ForeignKey(orm['userHandling.favorite'], null=False)),
            ('tag', models.ForeignKey(orm['userHandling.tag'], null=False))
        ))
        db.create_unique('Favorite_tags', ['favorite_id', 'tag_id'])

        # Changing field 'UserProfile.plaintextPreferred'
        db.alter_column('UserProfile', 'plaintextPreferred', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'UserProfile.wantsNewsletter'
        db.alter_column('UserProfile', 'wantsNewsletter', self.gf('django.db.models.fields.BooleanField')())

        # Changing field 'UserProfile.emailConfirmed'
        db.alter_column('UserProfile', 'emailConfirmed', self.gf('django.db.models.fields.BooleanField')())


    models = {
        'alerts.citation': {
            'Meta': {'ordering': "['caseNameFull']", 'object_name': 'Citation', 'db_table': "'Citation'"},
            'caseNameFull': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'caseNameShort': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            'caseNumber': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'blank': 'True'}),
            'citationUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'officialCitationLexis': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'officialCitationWest': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True'})
        },
        'alerts.court': {
            'Meta': {'ordering': "['courtUUID']", 'object_name': 'Court', 'db_table': "'Court'"},
            'courtShortName': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'courtURL': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'courtUUID': ('django.db.models.fields.CharField', [], {'max_length': '100', 'primary_key': 'True'})
        },
        'alerts.document': {
            'Meta': {'ordering': "['-time_retrieved']", 'object_name': 'Document', 'db_table': "'Document'"},
            'citation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['alerts.Citation']", 'null': 'True', 'blank': 'True'}),
            'court': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['alerts.Court']"}),
            'dateFiled': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'documentHTML': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'documentPlainText': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'documentSHA1': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'documentType': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'documentUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'download_URL': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'excerptSummary': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['alerts.ExcerptSummary']", 'null': 'True', 'blank': 'True'}),
            'judge': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['alerts.Judge']", 'null': 'True', 'blank': 'True'}),
            'local_path': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'party': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['alerts.Party']", 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '3', 'blank': 'True'}),
            'time_retrieved': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'alerts.excerptsummary': {
            'Meta': {'object_name': 'ExcerptSummary', 'db_table': "'ExcerptSummary'"},
            'autoExcerpt': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'courtSummary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'excerptUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'alerts.judge': {
            'Meta': {'ordering': "['court', 'canonicalName']", 'object_name': 'Judge', 'db_table': "'Judge'"},
            'canonicalName': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'court': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['alerts.Court']"}),
            'endDate': ('django.db.models.fields.DateField', [], {}),
            'judgeAvatar': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'judgeUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'startDate': ('django.db.models.fields.DateField', [], {})
        },
        'alerts.party': {
            'Meta': {'ordering': "['partyExtracted']", 'object_name': 'Party', 'db_table': "'Party'"},
            'partyExtracted': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'partyUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'userHandling.alert': {
            'Meta': {'ordering': "['alertFrequency', 'alertText']", 'object_name': 'Alert', 'db_table': "'Alert'"},
            'alertFrequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'alertName': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'alertPrivacy': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'alertText': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'alertUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastHitDate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sendNegativeAlert': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'userHandling.barmembership': {
            'Meta': {'ordering': "['barMembership']", 'object_name': 'BarMembership', 'db_table': "'BarMembership'"},
            'barMembership': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2'}),
            'barMembershipUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'userHandling.favorite': {
            'Meta': {'object_name': 'Favorite', 'db_table': "'Favorite'"},
            'doc_id': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['alerts.Document']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'max_length': '200'}),
            'notes': ('django.db.models.fields.TextField', [], {'max_length': '500'})
        },
        'userHandling.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'UserProfile'"},
            'activationKey': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'alert': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userHandling.Alert']", 'null': 'True', 'blank': 'True'}),
            'avatar': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'barmembership': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userHandling.BarMembership']", 'null': 'True', 'blank': 'True'}),
            'emailConfirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'favorite': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'users'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['userHandling.Favorite']"}),
            'key_expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'plaintextPreferred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'userProfileUUID': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'wantsNewsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['userHandling']
