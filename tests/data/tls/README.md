# Test-only TLS fixture

`leaf.pem` / `leaf.key` form a certificate for `localhost` issued by a throwaway
test CA ("KJ Des Test Root (not trusted anywhere)"). The CA's private key was
deleted after signing, and the CA certificate is not included or installed
anywhere. Tests use it to reproduce "unable to get local issuer certificate"
(OpenSSL error 20) on a local socket. It is never used outside the test suite.
