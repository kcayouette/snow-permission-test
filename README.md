# ServiceNow CRUD Permission Tester

Tests Create, Read, Update, and Delete permissions for a given ServiceNow account across all major ITSM and CSM modules. Cleans up all test records automatically after each run.

---

## Requirements

- Python 3
- `requests` library: `pip3 install requests`

---

## Usage

```bash
python3 snow_permission_test.py \
  --instance <instance_name> \
  --username <username> \
  --password <password> \
  [--output results.txt]
```

`--instance` is the subdomain only (e.g. `compassdcdev`, not the full URL).  
`--output` is optional — saves a clean plain-text copy of the results to the specified file.

### Example

```bash
python3 snow_permission_test.py \
  --instance compassdcdev \
  --username everbridge-integration \
  --password 'yourpassword' \
  --output results.txt
```

---

## Modules Tested

| Category  | Module               |
|-----------|----------------------|
| ITSM      | Incident             |
| ITSM      | Problem              |
| ITSM      | Change Request       |
| ITSM      | Change Task          |
| ITSM      | Service Request      |
| ITSM      | Requested Item       |
| ITSM      | Service Task         |
| ITSM      | Task (Generic)       |
| CMDB      | CMDB CI (Generic)    |
| CMDB      | CMDB CI Server       |
| Knowledge | Knowledge Article    |
| CSM       | CSM Case             |
| CSM       | CSM Account          |
| CSM       | CSM Contact          |

---

## Results

Each module reports PASS, FAIL, or SKIP per operation:

- **PASS** — operation succeeded
- **FAIL** — operation was denied or errored (HTTP status shown in Notes)
- **SKIP** — table not found or not licensed on this instance

All test records are automatically deleted after the run. Any records that could not be deleted are listed in the cleanup summary.

---

## Notes

- Incident records are submitted with `caller_id` set to the authenticated account's `sys_id`, resolved automatically before tests begin.
- All test records include a description noting they are automated test records and should not be actioned manually.
- Environment variables can be used instead of flags: `SNOW_INSTANCE`, `SNOW_USERNAME`, `SNOW_PASSWORD`.
