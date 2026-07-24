# PV AMLACS Storage

The Extranet does not generate PV documents. It retrieves the official PDF
downloaded from AMLACS and keeps it private.

Configure the shared private root in `.env`:

```text
PV_DOCUMENT_ROOT=C:\path\to\private\pv_documents
```

The root contains three folders:

```text
pv_documents/
  official/  # Official PDF downloaded from AMLACS. Never modified by Extranet.
  dr_signed/ # Copy signed by the owning DDE delegation.
  signed/    # Final copy signed by the beneficiary administration.
```

Place an official source PDF directly in `official/` using one of these names:

```text
<import_id>.pdf
<safe_num_dossier>.pdf
<safe_num_dossier>__<safe_numero_pv>.pdf
<safe_numero_pv>.pdf
<pv_key>.pdf
```

For example, source dossier `1003/199204/31`, PV `23/2010/04` can use either
`6.pdf`, `1003_199204_31.pdf`, `1003_199204_31__23_2010_04.pdf`, or
`23_2010_04.pdf` when its import id is `6`.

If no file matches, or more than one candidate matches, the Extranet refuses
to display or sign the PV. Once an OTP is requested, the source PDF hash is
recorded. If AMLACS replaces that file before verification, the OTP signature
is rejected and a new OTP must be requested.

## Signature stages

For an imported dossier whose exact PV status is `Validé`, the signataire of
the matching delegation can consult the official PDF and sign it by OTP. The
Extranet stores the resulting PAdES PDF under `dr_signed/` and records the
signature proof in managed Django tables. It does not update the unmanaged
AMLACS source row.

Once the delegation signature succeeds, the managed PV state makes the dossier
available to the signataire of the matching beneficiary administration. The
delegation can no longer consult or sign the document through its Extranet
queue.

The beneficiary does not sign a new copy made from `official/`. The Extranet
opens the existing `dr_signed/` PDF and appends the beneficiary signature as a
new incremental PAdES revision. The final document under `signed/` therefore
contains both cryptographic signatures:

```text
official/ -> delegation PAdES -> dr_signed/
dr_signed/ -> beneficiary PAdES -> signed/
```

The delegation signature covers the first signed revision. The beneficiary
signature covers the complete final file, including the delegation revision.
Final integrity verification requires both stored certificate fingerprints and
both embedded signature fields to validate.

## Development PAdES signature

After successful OTP verification, the Extranet:

1. adds the existing Arabic signature statement to the private signed copy;
2. applies an invisible PAdES-B-B cryptographic signature to that PDF;
3. records the signature field, certificate subject, serial number, and
   SHA-256 certificate fingerprint in the signature proof;
4. verifies the PDF hash and PAdES signature before DDE Admin allows access.

The PDF has no visible PAdES label or signature box. The Arabic footer remains
the visible signature statement. In the two-stage workflow, the delegation
PAdES field remains invisible and the beneficiary PAdES field uses its Arabic
footer as the signature appearance.

For this non-production implementation, each signature uses a self-signed
certificate generated in memory from the signataire's real first and last
name and the beneficiary administration. The private key is not written to
disk. Adobe Reader can detect the PDF signature and detect later changes, but
the certificate will not be trusted automatically because it is not issued by
a recognized certification authority.

This is not a qualified or production electronic-signature setup. Production
use requires an approved certificate provider, protected long-lived private
keys, an appropriate trust chain, timestamping, and a retention policy.
Previously signed PDFs are not modified retroactively; records without PAdES
proof are reported as non-verifiable.
