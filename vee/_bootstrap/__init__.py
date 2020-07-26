import ssl
import sys


def bootstrap_openssl():

    # NOTE: The logic here is lifted entirely from pip;
    # see https://github.com/pypa/pip/commit/9c037803197b05bb722223c2f5deffcbb7f4b0c4

    # We want to inject the use of SecureTransport as early as possible so that any
    # references or sessions or what have you are ensured to have it, however we
    # only want to do this in the case that we're running on macOS and the linked
    # OpenSSL is too old to handle TLSv1.2
    if sys.platform == "darwin" and ssl.OPENSSL_VERSION_NUMBER < 0x1000100f:  # OpenSSL 1.0.1
        import urllib3.contrib.securetransport
        urllib3.contrib.securetransport.inject_into_urllib3()


def bootstrap():
    bootstrap_openssl()

