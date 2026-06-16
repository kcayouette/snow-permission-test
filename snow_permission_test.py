"""
ServiceNow CRUD Permission Tester
Tests Create, Read, Update, Delete permissions across ITSM and CSM modules.
Cleans up all created records after testing.

Usage:
    python snow_permission_test.py --instance yourinstance \
                                   --username admin --password secret

    Or set environment variables:
        SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD
"""

import argparse
import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

# ── ANSI colors ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Modules to test ──────────────────────────────────────────────────────────
# Each entry: (display_name, table_name, create_payload)
MODULES = [
    # ── ITSM ──
    ("Incident",            "incident", {
        "short_description": "[PERM-TEST] Incident",
        "impact": "3", "urgency": "3"
    }),
    ("Problem",             "problem", {
        "short_description": "[PERM-TEST] Problem",
        "impact": "3", "urgency": "3"
    }),
    ("Change Request",      "change_request", {
        "short_description": "[PERM-TEST] Change Request",
        "type": "normal", "impact": "3", "risk": "4"
    }),
    ("Change Task",         "change_task", {
        "short_description": "[PERM-TEST] Change Task"
    }),
    ("Service Request",     "sc_request", {
        "short_description": "[PERM-TEST] Service Request"
    }),
    ("Requested Item",      "sc_req_item", {
        "short_description": "[PERM-TEST] Requested Item"
    }),
    ("Service Task",        "sc_task", {
        "short_description": "[PERM-TEST] Service Task"
    }),
    ("Task (Generic)",      "task", {
        "short_description": "[PERM-TEST] Generic Task"
    }),
    # ── CMDB ──
    ("CMDB CI (Generic)",   "cmdb_ci", {
        "name": "[PERM-TEST] CI",
        "short_description": "[PERM-TEST] CI"
    }),
    ("CMDB CI Server",      "cmdb_ci_server", {
        "name": "[PERM-TEST] Server CI"
    }),
    # ── Knowledge ──
    ("Knowledge Article",   "kb_knowledge", {
        "short_description": "[PERM-TEST] Knowledge Article",
        "text": "Permission test article body."
    }),
    # ── CSM ──
    ("CSM Case",            "sn_customerservice_case", {
        "short_description": "[PERM-TEST] CSM Case",
        "impact": "3", "urgency": "3"
    }),
    ("CSM Account",         "customer_account", {
        "name": "[PERM-TEST] Account"
    }),
    ("CSM Contact",         "customer_contact", {
        "first_name": "PermTest",
        "last_name":  "Contact",
        "email":      "permtest@example.invalid"
    }),
]

UPDATE_PAYLOAD = {"description": "[PERM-TEST] Updated by permission tester"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def tag(result: str) -> str:
    if result == "PASS":
        return f"{GREEN}PASS{RESET}"
    if result == "SKIP":
        return f"{YELLOW}SKIP{RESET}"
    return f"{RED}FAIL{RESET}"


class SnowTester:
    def __init__(self, instance: str, username: str, password: str):
        self.base   = instance.rstrip("/")
        self.auth   = HTTPBasicAuth(username, password)
        self.headers = {
            "Content-Type": "application/json",
            "Accept":       "application/json"
        }
        self.created: list[tuple[str, str]] = []   # (table, sys_id)
        self.results: list[dict]            = []

    def _url(self, table: str, sys_id: str = "") -> str:
        path = f"/api/now/table/{table}"
        if sys_id:
            path += f"/{sys_id}"
        return self.base + path

    def _req(self, method: str, url: str, **kwargs):
        try:
            r = requests.request(
                method, url, auth=self.auth, headers=self.headers,
                timeout=15, **kwargs
            )
            return r
        except requests.RequestException as e:
            return None

    # ── Single CRUD cycle ─────────────────────────────────────────────────

    def test_module(self, display: str, table: str, payload: dict):
        row = {"module": display, "table": table,
               "create": "—", "read": "—", "update": "—", "delete": "—",
               "note": ""}
        sys_id = None

        # CREATE
        r = self._req("POST", self._url(table), json=payload)
        if r is None:
            row["create"] = "FAIL"; row["note"] = "Connection error"
            self.results.append(row); return
        if r.status_code == 403:
            row["create"] = "FAIL"; row["note"] = "403 Forbidden"
            self.results.append(row); return
        if r.status_code == 404:
            row["create"] = "SKIP"; row["note"] = "Table not found / not licensed"
            self.results.append(row); return
        if r.status_code in (200, 201):
            sys_id = r.json().get("result", {}).get("sys_id")
            row["create"] = "PASS"
            if sys_id:
                self.created.append((table, sys_id))
        else:
            row["create"] = "FAIL"
            row["note"]   = f"HTTP {r.status_code}"
            self.results.append(row); return

        if not sys_id:
            row["create"] = "FAIL"; row["note"] = "No sys_id returned"
            self.results.append(row); return

        # READ
        r = self._req("GET", self._url(table, sys_id))
        if r and r.status_code == 200:
            row["read"] = "PASS"
        else:
            row["read"] = "FAIL"
            row["note"] = f"Read HTTP {getattr(r,'status_code','?')}"

        # UPDATE
        r = self._req("PATCH", self._url(table, sys_id), json=UPDATE_PAYLOAD)
        if r and r.status_code == 200:
            row["update"] = "PASS"
        elif r and r.status_code == 403:
            row["update"] = "FAIL"; row["note"] = "Update 403 Forbidden"
        else:
            row["update"] = "FAIL"
            row["note"]   = f"Update HTTP {getattr(r,'status_code','?')}"

        # DELETE
        r = self._req("DELETE", self._url(table, sys_id))
        if r and r.status_code == 204:
            row["delete"] = "PASS"
            self.created  = [(t, i) for t, i in self.created if i != sys_id]
        elif r and r.status_code == 403:
            row["delete"] = "FAIL"; row["note"] = "Delete 403 Forbidden"
        else:
            row["delete"] = "FAIL"
            row["note"]   = f"Delete HTTP {getattr(r,'status_code','?')}"

        self.results.append(row)

    # ── Cleanup leftover records ──────────────────────────────────────────

    def cleanup(self):
        if not self.created:
            return
        print(f"\n{YELLOW}Cleaning up {len(self.created)} leftover record(s)...{RESET}")
        for table, sys_id in self.created:
            r = self._req("DELETE", self._url(table, sys_id))
            status = r.status_code if r else "ERR"
            icon   = "✓" if r and r.status_code == 204 else "✗"
            print(f"  {icon} {table} / {sys_id}  [{status}]")

    # ── Print results table ───────────────────────────────────────────────

    def print_results(self):
        col_w = [30, 22, 8, 8, 8, 8, 30]
        headers = ["Module", "Table", "Create", "Read", "Update", "Delete", "Note"]

        sep = "+" + "+".join("-" * (w + 2) for w in col_w) + "+"
        def row_str(cells):
            return "|" + "|".join(
                f" {str(c):<{col_w[i]}} " for i, c in enumerate(cells)
            ) + "|"

        print(f"\n{BOLD}{CYAN}{'─'*60}")
        print("  ServiceNow CRUD Permission Test Results")
        print(f"{'─'*60}{RESET}\n")
        print(sep)
        print(row_str(headers))
        print(sep)

        pass_count = skip_count = fail_count = 0

        for r in self.results:
            cells = [
                r["module"], r["table"],
                r["create"], r["read"], r["update"], r["delete"],
                r.get("note", "")
            ]
            # Build colored row
            line = "|"
            for i, c in enumerate(cells):
                val = str(c)
                if i in (2, 3, 4, 5):   # CRUD columns
                    val = f" {tag(c):<{col_w[i]+9}} "   # +9 for ANSI escape bytes
                else:
                    val = f" {val:<{col_w[i]}} "
                line += val + "|"
            print(line)

            for op in (r["create"], r["read"], r["update"], r["delete"]):
                if op == "PASS":  pass_count += 1
                elif op == "SKIP": skip_count += 1
                elif op == "FAIL": fail_count += 1

        print(sep)
        total = pass_count + fail_count
        print(f"\n{BOLD}Summary:{RESET}  "
              f"{GREEN}{pass_count} PASS{RESET}  "
              f"{RED}{fail_count} FAIL{RESET}  "
              f"{YELLOW}{skip_count} SKIP{RESET}  "
              f"({total} operations tested)\n")

    # ── Run all ───────────────────────────────────────────────────────────

    def run(self):
        print(f"\n{BOLD}Instance:{RESET} {self.base}")
        print(f"{BOLD}Testing {len(MODULES)} modules...{RESET}\n")

        for display, table, payload in MODULES:
            print(f"  Testing {display:<30}", end="", flush=True)
            self.test_module(display, table, payload)
            last = self.results[-1]
            ops  = [last["create"], last["read"], last["update"], last["delete"]]
            icons = "".join(
                f"{GREEN}✓{RESET}" if o == "PASS"
                else f"{YELLOW}~{RESET}" if o == "SKIP"
                else f"{RED}✗{RESET}"
                for o in ops
            )
            print(f"  C{icons[0:5]}R{icons[5:10]}U{icons[10:15]}D{icons[15:20]}")

        self.cleanup()
        self.print_results()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test CRUD permissions on a ServiceNow instance."
    )
    parser.add_argument("--instance", default=os.getenv("SNOW_INSTANCE"),
                        help="ServiceNow instance name (e.g. dev12345)")
    parser.add_argument("--username", default=os.getenv("SNOW_USERNAME"),
                        help="Username")
    parser.add_argument("--password", default=os.getenv("SNOW_PASSWORD"),
                        help="Password")
    args = parser.parse_args()

    if not all([args.instance, args.username, args.password]):
        print(f"{RED}Error:{RESET} Provide --instance, --username, --password "
              f"(or set SNOW_INSTANCE / SNOW_USERNAME / SNOW_PASSWORD).")
        sys.exit(1)

    instance_url = f"https://{args.instance}.service-now.com"
    tester = SnowTester(instance_url, args.username, args.password)
    try:
        tester.run()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted — cleaning up...{RESET}")
        tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
