
# core/views.py
# ---------------------------------------------
# Django views for tfar1 (cloud-first, Railway-ready)
# Upload .xlsx (15 columns), validate, store, display, download CSV
# ---------------------------------------------

import io
from typing import Any, List

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect

from .forms import UploadForm
from .models import TfarRecord

# Expected headers (case-insensitive match; exact order required)
REQUIRED_HEADERS: List[str] = [
    "asset id",
    "asset description",
    "tax start date",
    "depreciation method",
    "purchase cost",
    "tax effective life",
    "opening cost",
    "opening accumulated depreciation",
    "opening wdv",
    "addition",
    "disposal",
    "tax depreciation",
    "closing cost",
    "closing accumulated depreciation",
    "closing wdv",
]


def _cell_value(row: tuple[Cell | Any, ...], index: int) -> Any:
    """Safe accessor for an Excel row tuple."""
    try:
        return row[index]
    except Exception:
        return None


def _to_int(value: Any) -> int:
    """Convert Excel cell value to int, defaulting to 0 for blanks / None."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 0
    try:
        # some Excel numeric cells come as float; cast safely
        return int(round(float(value)))
    except Exception:
        # bubble up a descriptive ValueError for the UI
        raise ValueError(f"Cannot convert '{value}' to integer")


def _to_str(value: Any, max_len: int) -> str:
    """Convert to string (safe), truncate to max_len."""
    s = "" if value is None else str(value)
    return s[:max_len]


def _to_date(value: Any):
    """
    Convert Excel cell value to Python date.
    openpyxl returns datetime.date or datetime.datetime for date cells automatically
    when data_only=True; if it's a string, try ISO parse.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ValueError("Tax Start Date is required")

    # If already a date/datetime-like object
    try:
        # attempt to access .date() (datetime)
        if hasattr(value, "date"):
            return value.date()
    except Exception:
        pass

    # If it's already a date (openpyxl may use date class)
    from datetime import date
    if isinstance(value, date):
        return value

    # Fallback: attempt string parse (ISO-like)
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        # You can expand formats as needed
        raise ValueError(f"Cannot parse date '{value}'")


# -----------------------
# Authentication views
# -----------------------

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")
        return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# -----------------------
# Dashboard & data views
# -----------------------

@login_required
def dashboard(request):
    rows = (
        TfarRecord.objects.filter(owner=request.user)
        .order_by("-uploaded_at", "asset_id")[:500]
    )
    return render(request, "dashboard.html", {"rows": rows})


@login_required
def upload_tfar(request):
    """
    Upload an .xlsx TFAR file with exactly 15 headers.
    Stores rows for the authenticated user and redirects to dashboard on success.
    """
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "upload.html", {"form": form, "error": "Invalid form submission."})

        uploaded = request.FILES.get("file")
        if not uploaded:
            return render(request, "upload.html", {"form": form, "error": "Please choose a file to upload."})

        if not uploaded.name.lower().endswith(".xlsx"):
            return render(
                request,
                "upload.html",
                {"form": form, "error": "Unsupported file type. Please upload .xlsx files only."},
            )

        # Load first worksheet
        try:
            wb = load_workbook(filename=uploaded, data_only=True)
            ws = wb.active
        except Exception as e:
            return render(request, "upload.html", {"form": form, "error": f"Failed to read Excel file: {e}"})

        # Read header row (row 1)
        header_cells = ws[1]
        headers = [(_c.value if _c.value is not None else "").strip().lower() for _c in header_cells]
        if len(headers) != 15 or headers != REQUIRED_HEADERS:
            expected = ", ".join(REQUIRED_HEADERS)
            found = ", ".join(headers)
            return render(
                request,
                "upload.html",
                {
                    "form": form,
                    "error": f"Column mismatch.\nExpected (15): {expected}\nFound (15): {found}",
                },
            )

        # Parse remaining rows and bulk insert
        records_to_create: list[TfarRecord] = []
        row_num = 1  # header
        try:
            for row in ws.iter_rows(min_row=2, values_only=True):
                row_num += 1

                # Skip empty lines (all None)
                if row is None or all(v is None or (isinstance(v, str) and v.strip() == "") for v in row):
                    continue

                # Map cells by position to your model fields
                rec = TfarRecord(
                    owner=request.user,

                    asset_id=_to_str(_cell_value(row, 0), 50),
                    asset_description=_to_str(_cell_value(row, 1), 250),
                    tax_start_date=_to_date(_cell_value(row, 2)),
                    depreciation_method=_to_str(_cell_value(row, 3), 50),

                    purchase_cost=_to_int(_cell_value(row, 4)),
                    tax_effective_life=_to_int(_cell_value(row, 5)),
                    opening_cost=_to_int(_cell_value(row, 6)),
                    opening_accum_depreciation=_to_int(_cell_value(row, 7)),
                    opening_wdv=_to_int(_cell_value(row, 8)),
                    addition=_to_int(_cell_value(row, 9)),
                    disposal=_to_int(_cell_value(row, 10)),
                    tax_depreciation=_to_int(_cell_value(row, 11)),
                    closing_cost=_to_int(_cell_value(row, 12)),
                    closing_accum_depreciation=_to_int(_cell_value(row, 13)),
                    closing_wdv=_to_int(_cell_value(row, 14)),
                )
                records_to_create.append(rec)
        except ValueError as ve:
            # Provide row context for easier troubleshooting
            return render(
                request,
                "upload.html",
                {"form": form, "error": f"Row {row_num}: {ve}"},
            )
        except Exception as e:
            return render(
                request,
                "upload.html",
                {"form": form, "error": f"Unexpected error on row {row_num}: {e}"},
            )

        # Persist all rows
        if records_to_create:
            TfarRecord.objects.bulk_create(records_to_create, batch_size=1000)

        return redirect("dashboard")

    # GET
    return render(request, "upload.html", {"form": UploadForm()})


@login_required
def download_tfar_csv(request):
    """
    Stream the current user's TFAR rows as CSV (15 headers).
    """
    qs = TfarRecord.objects.filter(owner=request.user).order_by("asset_id")

    out = io.StringIO()
    out.write(",".join(REQUIRED_HEADERS) + "\n")

    for r in qs:
        out.write(",".join([
            r.asset_id,
            r.asset_description,
            r.tax_start_date.isoformat(),
            r.depreciation_method,
            str(r.purchase_cost),
            str(r.tax_effective_life),
            str(r.opening_cost),
            str(r.opening_accum_depreciation),
            str(r.opening_wdv),
            str(r.addition),
            str(r.disposal),
            str(r.tax_depreciation),
            str(r.closing_cost),
            str(r.closing_accum_depreciation),
            str(r.closing_wdv),
        ]) + "\n")

    response = HttpResponse(out.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tfar_export.csv"'
    return response
