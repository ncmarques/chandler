"""
Unit tests for mail
"""

__revision__  = "$Revision$"
__date__      = "$Date$"
__copyright__ = "Copyright (c) 2003 Open Source Applications Foundation"
__license__   = "http://osafoundation.org/Chandler_0.1_license_terms.htm"

import unittest, os

import OSAF.contentmodel.tests.TestContentModel as TestContentModel
import OSAF.contentmodel.mail.Mail as Mail

import mx.DateTime as DateTime

class MailTest(TestContentModel.ContentModelTestCase):
    """ Test Mail Content Model """

    def testMail(self):
        """ Simple test for creating instances of email related kinds """

        def _verifyMailMessage(message):
            pass

        # Test the globals
        mailPath = '//parcels/OSAF/contentmodel/mail/%s'

        self.assertEqual(Mail.AttachmentKind,
                         self.rep.find(mailPath % 'Attachment'))
        self.assertEqual(Mail.EmailAccountKind,
                         self.rep.find(mailPath % 'EmailAccount'))
        self.assertEqual(Mail.EmailAddressKind,
                         self.rep.find(mailPath % 'EmailAddress'))
        self.assertEqual(Mail.MailMessageKind,
                         self.rep.find(mailPath % 'MailMessage'))

        # Construct sample items
        attachmentItem = Mail.Attachment("attachmentItem")
        emailAccountItem = Mail.EmailAccount("emailAccountItem")
        emailAddressItem = Mail.EmailAddress("emailAddressItem")
        mailMessageItem = Mail.MailMessage("mailMessageItem")

        # Double check kinds
        self.assertEqual(attachmentItem.kind, Mail.AttachmentKind)
        self.assertEqual(emailAccountItem.kind, Mail.EmailAccountKind)
        self.assertEqual(emailAddressItem.kind, Mail.EmailAddressKind)
        self.assertEqual(mailMessageItem.kind, Mail.MailMessageKind)

        # Literal properties
        mailMessageItem.subject = "Hello"
        mailMessageItem.spamScore = 5

        _verifyMailMessage(mailMessageItem)

        self._reopenRepository()

        contentItemParent = self.rep.find("//userdata/contentitems")
        
        mailMessageItem = contentItemParent.find("mailMessageItem")
        _verifyMailMessage(mailMessageItem)
        

if __name__ == "__main__":
    unittest.main()
