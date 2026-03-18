"""Generate seed_data.sql with realistic, deterministic demo data.

Run once to (re)generate ``seed_data.sql``. A fixed RNG seed keeps the dataset
stable across runs so example answers in the README stay correct.

    python seed/generate_seed.py
"""
from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

RNG = random.Random(71)  # fixed seed -> reproducible dataset

OUT = Path(__file__).parent / "seed_data.sql"

PRODUCTS = [
    ("Cardiostat", "tablet", "10 mg", "cardiology"),
    ("Cardiostat", "tablet", "20 mg", "cardiology"),
    ("Neuroxen", "capsule", "75 mg", "neurology"),
    ("Oncovera", "injection", "50 mg/mL", "oncology"),
    ("Oncovera", "injection", "100 mg/mL", "oncology"),
    ("Respiclear", "syrup", "5 mg/5 mL", "respiratory"),
    ("Gastroease", "tablet", "40 mg", "gastroenterology"),
    ("Dermasoft", "ointment", "2%", "dermatology"),
    ("Immunoboost", "capsule", "250 mg", "immunology"),
    ("Painaway", "tablet", "500 mg", "analgesics"),
    ("Diabetrol", "tablet", "850 mg", "endocrinology"),
    ("Antibex", "capsule", "500 mg", "anti-infectives"),
]

EQUIPMENT = [
    ("Tablet Press TP-100", "tablet press", "Block A - Line 1", "operational"),
    ("Tablet Press TP-200", "tablet press", "Block A - Line 2", "operational"),
    ("Tablet Press TP-300", "tablet press", "Block A - Line 3", "maintenance"),
    ("Encapsulator EC-50", "encapsulator", "Block B - Line 1", "operational"),
    ("Encapsulator EC-60", "encapsulator", "Block B - Line 2", "operational"),
    ("Autoclave AC-1", "autoclave", "Sterile Block - Suite 1", "operational"),
    ("Autoclave AC-2", "autoclave", "Sterile Block - Suite 2", "operational"),
    ("Lyophilizer LY-1", "lyophilizer", "Sterile Block - Suite 3", "maintenance"),
    ("Coating Pan CP-10", "coating pan", "Block A - Line 4", "operational"),
    ("Coating Pan CP-20", "coating pan", "Block A - Line 5", "decommissioned"),
    ("Granulator GR-1", "granulator", "Block C - Line 1", "operational"),
    ("Granulator GR-2", "granulator", "Block C - Line 2", "operational"),
    ("Filling Line FL-1", "filling line", "Sterile Block - Suite 4", "operational"),
    ("Blister Packer BP-1", "blister packer", "Packaging - Line 1", "operational"),
    ("Mixer MX-5", "mixer", "Block C - Line 3", "operational"),
]

FIRST_NAMES = [
    "Aisha", "Brendan", "Chen", "Deirdre", "Emeka", "Fiona", "Gabriel", "Hana",
    "Imran", "Julia", "Kemal", "Liam", "Maria", "Niamh", "Omar", "Priya",
    "Quentin", "Roisin", "Sven", "Tara", "Usman", "Vera", "Wei", "Yara",
]
LAST_NAMES = [
    "Okafor", "Murphy", "Lin", "Walsh", "Ahmed", "Byrne", "Santos", "Kim",
    "Khan", "Novak", "Costa", "Reilly", "Singh", "Doyle", "Haddad", "Patel",
]
ROLES = ["operator", "operator", "operator", "supervisor", "qa_analyst"]
DEPARTMENTS = ["Manufacturing", "Quality Control", "Packaging", "Sterile Operations"]

QC_TESTS = {
    "assay": (95.0, 105.0),       # % of label claim
    "dissolution": (80.0, 100.0),  # % released at 30 min
    "hardness": (4.0, 12.0),       # kp
    "microbial": (0.0, 100.0),     # CFU/g (lower better; spec as max)
}

DEVIATION_TYPES = [
    "temperature excursion", "equipment failure", "out-of-specification result",
    "documentation error", "power interruption", "yield deviation",
    "environmental monitoring excursion", "cleaning failure",
]


def esc(value: str) -> str:
    return value.replace("'", "''")


def rand_date(start: dt.date, end: dt.date) -> dt.date:
    delta = (end - start).days
    return start + dt.timedelta(days=RNG.randint(0, delta))


def build() -> str:
    lines: list[str] = ["BEGIN;", ""]

    # products
    lines.append(
        "INSERT INTO products (name, dosage_form, strength, therapeutic_area) VALUES"
    )
    rows = [
        f"  ('{esc(n)}', '{esc(d)}', '{esc(s)}', '{esc(t)}')"
        for (n, d, s, t) in PRODUCTS
    ]
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    # equipment
    lines.append(
        "INSERT INTO equipment (name, equipment_type, location, status, installed_date) VALUES"
    )
    rows = []
    for (n, et, loc, st) in EQUIPMENT:
        installed = rand_date(dt.date(2018, 1, 1), dt.date(2022, 12, 31))
        rows.append(
            f"  ('{esc(n)}', '{esc(et)}', '{esc(loc)}', '{esc(st)}', '{installed.isoformat()}')"
        )
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    # operators
    lines.append("INSERT INTO operators (name, role, department) VALUES")
    rows = []
    used = set()
    for _ in range(20):
        while True:
            name = f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}"
            if name not in used:
                used.add(name)
                break
        role = RNG.choice(ROLES)
        dept = (
            "Quality Control" if role == "qa_analyst" else RNG.choice(DEPARTMENTS)
        )
        rows.append(f"  ('{esc(name)}', '{esc(role)}', '{esc(dept)}')")
    lines.append(",\n".join(rows) + ";")
    lines.append("")

    n_products = len(PRODUCTS)
    n_equipment = len(EQUIPMENT)
    n_operators = 20
    operational_equipment = [
        i + 1 for i, e in enumerate(EQUIPMENT) if e[3] == "operational"
    ]

    # batches
    n_batches = 320
    lines.append(
        "INSERT INTO batches (batch_number, product_id, equipment_id, operator_id, "
        "manufactured_date, quantity_units, status) VALUES"
    )
    batch_rows = []
    batch_meta = []  # (batch_id, mfg_date, status)
    for i in range(1, n_batches + 1):
        batch_no = f"B-{2023 + (i % 2)}-{i:04d}"
        product_id = RNG.randint(1, n_products)
        equipment_id = RNG.choice(operational_equipment)
        operator_id = RNG.randint(1, n_operators)
        mfg = rand_date(dt.date(2023, 1, 1), dt.date(2024, 12, 31))
        qty = RNG.choice([50000, 75000, 100000, 120000, 150000, 200000])
        # Status distribution: mostly released, some quarantine, fewer rejected.
        roll = RNG.random()
        status = "released" if roll < 0.82 else ("quarantine" if roll < 0.92 else "rejected")
        batch_rows.append(
            f"  ('{batch_no}', {product_id}, {equipment_id}, {operator_id}, "
            f"'{mfg.isoformat()}', {qty}, '{status}')"
        )
        batch_meta.append((i, mfg, status))
    lines.append(",\n".join(batch_rows) + ";")
    lines.append("")

    # qc_tests: each batch gets assay + dissolution + sometimes hardness/microbial.
    lines.append(
        "INSERT INTO qc_tests (batch_id, test_name, result, measured_value, "
        "spec_min, spec_max, tested_date) VALUES"
    )
    qc_rows = []
    for (bid, mfg, status) in batch_meta:
        tested = mfg + dt.timedelta(days=RNG.randint(1, 5))
        tests = ["assay", "dissolution"]
        if RNG.random() < 0.6:
            tests.append("hardness")
        if RNG.random() < 0.3:
            tests.append("microbial")
        for test in tests:
            lo, hi = QC_TESTS[test]
            # Rejected batches are far more likely to carry a failing test.
            fail_chance = 0.6 if status == "rejected" else (0.15 if status == "quarantine" else 0.03)
            failing = RNG.random() < fail_chance
            if test == "microbial":
                spec_min, spec_max = 0.0, 100.0
                value = RNG.uniform(101.0, 400.0) if failing else RNG.uniform(0.0, 80.0)
            else:
                spec_min, spec_max = lo, hi
                if failing:
                    value = (
                        RNG.uniform(lo - 8, lo - 0.5)
                        if RNG.random() < 0.5
                        else RNG.uniform(hi + 0.5, hi + 8)
                    )
                else:
                    value = RNG.uniform(lo + 0.5, hi - 0.5)
            result = "fail" if failing else "pass"
            qc_rows.append(
                f"  ({bid}, '{test}', '{result}', {round(value, 3)}, "
                f"{spec_min}, {spec_max}, '{tested.isoformat()}')"
            )
    lines.append(",\n".join(qc_rows) + ";")
    lines.append("")

    # deviations
    lines.append(
        "INSERT INTO deviations (batch_id, equipment_id, deviation_type, severity, "
        "status, description, reported_date, closed_date) VALUES"
    )
    dev_rows = []
    n_deviations = 90
    for _ in range(n_deviations):
        bid, mfg, status = RNG.choice(batch_meta)
        equipment_id = RNG.choice(operational_equipment + [3, 8])  # include some in-maintenance
        dtype = RNG.choice(DEVIATION_TYPES)
        sev_roll = RNG.random()
        severity = "minor" if sev_roll < 0.5 else ("major" if sev_roll < 0.85 else "critical")
        reported = mfg + dt.timedelta(days=RNG.randint(0, 10))
        is_closed = RNG.random() < 0.7
        if is_closed:
            closed = reported + dt.timedelta(days=RNG.randint(2, 45))
            closed_sql = f"'{closed.isoformat()}'"
            dev_status = "closed"
        else:
            closed_sql = "NULL"
            dev_status = "open"
        desc = f"{dtype.capitalize()} observed during processing of batch {bid}."
        dev_rows.append(
            f"  ({bid}, {equipment_id}, '{esc(dtype)}', '{severity}', "
            f"'{dev_status}', '{esc(desc)}', '{reported.isoformat()}', {closed_sql})"
        )
    lines.append(",\n".join(dev_rows) + ";")
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT}")
