#!/usr/bin/env python

"""
How to create a non-CA certificate with Python.

WARNING: This sample only demonstrates how to use the objects and methods,
         not how to create a safe and correct certificate.

Copyright (c) 2004 Open Source Applications Foundation.
Author: Heikki Toivonen
"""

from M2Crypto import RSA, X509, EVP, m2, Rand, Err
import ca

# XXX Do I actually need more keys?
# XXX Check return values from functions

def generateRSAKey():
    return RSA.gen_key(2048, m2.RSA_F4)

def makePKey(key):
    pkey = EVP.PKey()
    pkey.assign_rsa(key)
    return pkey
    
def makeRequest(pkey):
    req = X509.Request()
    req.set_version(0)# Seems to default to 0, but we can now set it as well
    req.set_pubkey(pkey)
    name = X509.X509_Name()
    name.CN = 'Some Individual'
    req.set_subject(name)
    # XXX Extensions
    req.sign(pkey, 'sha1')
    return req

def makeCert(req, caCert, caPKey):
    pkey = req.get_pubkey()
    #woop = makePKey(generateRSAKey())
    #if not req.verify(woop.pkey):
    if not req.verify(pkey):
        # XXX What error object should I use?
        raise ValueError, 'Error verifying request'
    sub = req.get_subject()
    # If this were a real certificate request, you would display
    # all the relevant data from the request and ask a human operator
    # if you were sure. Now we just create the certificate blindly based
    # on the request.
    cert = X509.X509()
    cert.set_version(2)
    cert.set_serial_number(caCert.get_serial_number()+1)
    print '***Serial: ', cert.get_serial_number()
    cert.set_subject(sub)
    issuer = caCert.get_subject()
    cert.set_issuer(issuer)
    cert.set_pubkey(EVP.PKey(pkey))
    notBefore = m2.x509_get_not_before(cert.x509)
    notAfter  = m2.x509_get_not_after(cert.x509)
    m2.x509_gmtime_adj(notBefore, 0)
    days = 30
    m2.x509_gmtime_adj(notAfter, 60*60*24*days)
    # XXX extensions
    cert.sign(caPKey, 'sha1')
    return cert

if __name__ == '__main__':
    Rand.load_file('../randpool.dat', -1)
    key = generateRSAKey()
    pkey = makePKey(key)
    req = makeRequest(pkey)
    print req.as_text()
    (caCert, caPKey) = ca.ca()
    cert = makeCert(req, caCert, caPKey)
    print cert.as_text()
    Rand.save_file('../randpool.dat')
