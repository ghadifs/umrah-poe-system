import io
import sqlite3
import pandas as pd
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "umrah_poe.db"

SHEET_TABLE = {
    "القدوم اليومي":                       "daily_arrivals",
    "اشتراط ـ الحمى الشوكية":              "meningitis",
    "اشتراط ـ شلل الأطفال":               "polio",
    "اشتراط ـ الحمى الصفراء":             "yellow_fever",
    "حالات الاشتباه":                      "suspected",
    "الوفيات":                             "deaths",
    "النقل الطبي":                         "medical",
    "القادمين من دول أفريقيا المستهدفة":  "africa_targeted",
}


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS daily_arrivals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد القادمين" INTEGER,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS meningitis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد المعتمرين" INTEGER,
            "عدد الملتزمين" INTEGER,
            "غير الملتزمين" INTEGER,
            "نسبة الالتزام" REAL,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS polio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد المعتمرين" INTEGER,
            "عدد الملتزمين" INTEGER,
            "غير الملتزمين" INTEGER,
            "نسبة الالتزام" REAL,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS yellow_fever (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد المعتمرين" INTEGER,
            "عدد الملتزمين" INTEGER,
            "غير الملتزمين" INTEGER,
            "نسبة الالتزام" REAL,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS suspected (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد حالات الاشتباه" INTEGER,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS deaths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد الوفيات" INTEGER,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS medical (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "عدد حالات النقل الطبي" INTEGER,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ")
        );
        CREATE TABLE IF NOT EXISTS africa_targeted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            "الفترة" TEXT,
            "تاريخ إعداد التقرير" TEXT,
            "اسم المنفذ" TEXT,
            "وقت الإدخال" TEXT,
            "الجنسية" TEXT,
            "معتمرين" INTEGER,
            "أخرى" INTEGER,
            "الإجمالي" INTEGER,
            "حالات الاشتباه" INTEGER,
            UNIQUE("تاريخ إعداد التقرير","اسم المنفذ","الجنسية")
        );
        """)


def read_sheet(sheet_name: str) -> pd.DataFrame:
    table = SHEET_TABLE.get(sheet_name)
    if not table:
        return pd.DataFrame()
    with _conn() as con:
        try:
            df = pd.read_sql(f'SELECT * FROM "{table}" ORDER BY id', con)
            return df.drop(columns=["id"], errors="ignore")
        except Exception:
            return pd.DataFrame()


def load_all_sheets() -> dict:
    return {sheet: read_sheet(sheet) for sheet in SHEET_TABLE}


def upsert_port_period_row(sheet_name: str, row: dict, allow_update: bool = False):
    """Returns (ok: bool, error_msg: str)."""
    table = SHEET_TABLE.get(sheet_name)
    if not table:
        return False, "جدول غير موجود"

    report_date = str(row.get("تاريخ إعداد التقرير", ""))
    port_name   = str(row.get("اسم المنفذ", ""))

    with _conn() as con:
        cur = con.execute(
            f'SELECT COUNT(*) FROM "{table}" '
            f'WHERE "تاريخ إعداد التقرير"=? AND "اسم المنفذ"=?',
            (report_date, port_name),
        )
        exists = cur.fetchone()[0] > 0

        if exists and not allow_update:
            return False, (
                "يوجد تقرير محفوظ مسبقًا لهذا المنفذ في نفس التاريخ. "
                "فعّل وضع تعديل البيانات السابقة إذا رغبت في تحديثه."
            )

        if exists:
            con.execute(
                f'DELETE FROM "{table}" '
                f'WHERE "تاريخ إعداد التقرير"=? AND "اسم المنفذ"=?',
                (report_date, port_name),
            )

        cols         = '", "'.join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        con.execute(
            f'INSERT INTO "{table}" ("{cols}") VALUES ({placeholders})',
            list(row.values()),
        )

    return True, ""


def upsert_africa_row(row: dict) -> None:
    table       = "africa_targeted"
    report_date = str(row.get("تاريخ إعداد التقرير", ""))
    port_name   = str(row.get("اسم المنفذ", ""))
    nationality = str(row.get("الجنسية", ""))

    with _conn() as con:
        con.execute(
            f'DELETE FROM "{table}" '
            f'WHERE "تاريخ إعداد التقرير"=? AND "اسم المنفذ"=? AND "الجنسية"=?',
            (report_date, port_name, nationality),
        )
        cols         = '", "'.join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        con.execute(
            f'INSERT INTO "{table}" ("{cols}") VALUES ({placeholders})',
            list(row.values()),
        )


def export_to_excel_bytes(sheet_names: list) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name in sheet_names:
            read_sheet(sheet_name).to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()
