#!/bin/sh
# Runs a command with an optional extra root CA trusted, for builds behind a TLS-inspecting proxy.
# The CA arrives as the BuildKit secret "extra_ca" (never stored in an image layer); with an empty secret
# this is a plain pass-through and certificate verification is unchanged.
if [ -s /run/secrets/extra_ca ]; then
    cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca-bundle.pem
    export SSL_CERT_FILE=/tmp/ca-bundle.pem REQUESTS_CA_BUNDLE=/tmp/ca-bundle.pem PIP_CERT=/tmp/ca-bundle.pem CURL_CA_BUNDLE=/tmp/ca-bundle.pem
fi
exec "$@"
