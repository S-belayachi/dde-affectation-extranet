# PV AMLACS Storage

The Extranet does not generate PV documents. It retrieves the official PDF
downloaded from AMLACS and keeps it private.

Configure the shared private root in `.env`:

```text
PV_DOCUMENT_ROOT=C:\path\to\private\pv_documents
```

The root contains two folders:

```text
pv_documents/
  official/  # Official PDF downloaded from AMLACS. Never modified by Extranet.
  signed/    # Signed PDF copy created after successful OTP verification.
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
