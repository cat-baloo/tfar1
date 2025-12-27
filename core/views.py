
# core/views.py
import io, hashlib
from typing import Any, List
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from .forms import UploadForm, ClientSelectForm
from .models import TfarRecord, Client, ClientMembership, TfarUpload, TfarExport

# Required headers (case-insensitive, any order allowed in this Option B impl)
REQUIRED_HEADERS: List[str] = [
    "asset id", "asset description", "tax start date", "depreciation method",
    "purchase cost", "tax effective life", "opening cost",
    "opening accumulated depreciation", "opening wdv",
    "addition", "disposal", "tax depreciation",
    "closing cost", "closing accumulated depreciation", "closing wdv",
]
OPTIONAL_CLIENT_HEADER = "client"


def _cell_value(row: tuple[Cell | Any, ...], index: int) -> Any:
    try: return row[index]
    except Exception: return None

def _to_int(value: Any) -> int:
    if value is None or (isinstance(value, str) and value.strip() == ""): return 0
    try: return int(round(float(value)))
    except Exception: raise ValueError(f"Cannot convert '{value}' to integer")

def _to_str(value: Any, max_len: int) -> str:
    s = "" if value is None else str(value)
    return s[:max_len]

def _to_date(value: Any):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise ValueError("Tax Start Date is required")
    try:
        if hasattr(value, "date"): return value.date()
    except Exception: pass
    from datetime import date, datetime
    if isinstance(value, date): return value
    try: return datetime.fromisoformat(str(value)).date()
    except Exception: raise ValueError(f"Cannot parse date '{value}'")

def _get_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


# ------------- Auth -------------

def login_view(request):
    if request.method == "POST":
        u = request.POST.get("username"); p = request.POST.get("password")
        user = authenticate(request, username=u, password=p)
        if user: login(request, user); return redirect("dashboard")
        return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

def logout_view(request):
    logout(request); return redirect("login")


# ------------- Dashboard -------------

@login_required
def dashboard(request):
    memberships = ClientMembership.objects.filter(user=request.user).select_related("client").order_by("client__name")
    if not memberships.exists():
        return render(request, "dashboard.html", {
            "rows": [], "form": None, "client": None,
            "error": "You are not assigned to any clients. Please ask an administrator to add you."
        })

    selected_client_id = request.POST.get("client") or request.session.get("selected_client_id") \
                         or str(memberships.first().client.id)
    request.session["selected_client_id"] = selected_client_id

    client = get_object_or_404(Client, id=selected_client_id)
    if not memberships.filter(client=client).exists():
        return render(request, "dashboard.html", {"rows": [], "form": ClientSelectForm(user=request.user),
                                                  "error": "You don't have access to this client."})

    # PERMISSIONS: show ALL records for the client (not only owner's)
    rows = TfarRecord.objects.filter(client=client).order_by("-uploaded_at", "asset_id")[:2000]

    form = ClientSelectForm(user=request.user, data={"client": selected_client_id})
    return render(request, "dashboard.html", {"rows": rows, "form": form, "client": client})


# ------------- Upload -------------

@login_required
def upload_tfar(request):
    """
    Upload an .xlsx TFAR file with:
    - exactly the 15 required headers, or
    - those 15 plus an optional 'client' column (must match selected client).
    Only users with role 'preparer' for the client can upload.
    """
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return render(request, "upload.html", {"form": form, "error": "Invalid form submission."})

        uploaded = request.FILES.get("file")
        client_id = form.cleaned_data.get("client")
        if not uploaded: return render(request, "upload.html", {"form": form, "error": "Please choose a file to upload."})
        if not uploaded.name.lower().endswith(".xlsx"):
            return render(request, "upload.html", {"form": form, "error": "Upload .xlsx files only."})

        client = get_object_or_404(Client, id=client_id)
        membership = ClientMembership.objects.filter(user=request.user, client=client).first()
        if not membership:
            return render(request, "upload.html", {"form": form, "error": "You don't have access to this client."})
        if membership.role != "preparer":
            return render(request, "upload.html", {"form": form, "error": "Upload not permitted for Reviewer role."})

        try:
            wb = load_workbook(filename=uploaded, data_only=True); ws = wb.active
        except Exception as e:
            return render(request, "upload.html", {"form": form, "error": f"Failed to read Excel: {e}"})

        headers = [(_c.value or "").strip().lower() for _c in ws[1]]
        def headers_ok(hdrs):
            base_ok = all(h in hdrs for h in REQUIRED_HEADERS) and len(hdrs) in (15, 16)
            return base_ok and (len(hdrs) == 15 or OPTIONAL_CLIENT_HEADER in hdrs)
        if not headers_ok(headers):
            expected = ", ".join(REQUIRED_HEADERS) + " [optional: client]"
            return render(request, "upload.html", {"form": form,
                "error": "Column mismatch. Expected 15 headers, or 16 including 'client'. Required: " + expected})

        # map header index
        idx = {name: headers.index(name) for name in headers}
        has_client_col = OPTIONAL_CLIENT_HEADER in idx
        selected_client_name = client.name.strip().lower()

        # optional checksum of the uploaded file for audit
        uploaded.file.seek(0)
        checksum = hashlib.sha256(uploaded.file.read()).hexdigest()
        uploaded.file.seek(0)

        records_to_create = []
        row_num = 1
        try:
            for row in ws.iter_rows(min_row=2, values_only=True):
                row_num += 1
                if row is None or all(v is None or (isinstance(v, str) and v.strip() == "") for v in row):
                    continue
                if has_client_col:
                    file_client = str(row[idx[OPTIONAL_CLIENT_HEADER]] or "").strip().lower()
                    if not file_client: raise ValueError("Missing client value in 'client' column")
                    if file_client != selected_client_name:
                        raise ValueError(f"Client mismatch in row {row_num}: '{file_client}' vs '{selected_client_name}'")

                rec = TfarRecord(
                    owner=request.user, client=client,
                    asset_id=_to_str(row[idx["asset id"]], 50),
                    asset_description=_to_str(row[idx["asset description"]], 250),
                    tax_start_date=_to_date(row[idx["tax start date"]]),
                    depreciation_method=_to_str(row[idx["depreciation method"]], 50),
                    purchase_cost=_to_int(row[idx["purchase cost"]]),
                    tax_effective_life=_to_int(row[idx["tax effective life"]]),
                    opening_cost=_to_int(row[idx["opening cost"]]),
                    opening_accum_depreciation=_to_int(row[idx["opening accumulated depreciation"]]),
                    opening_wdv=_to_int(row[idx["opening wdv"]]),
                    addition=_to_int(row[idx["addition"]]),
                    disposal=_to_int(row[idx["disposal"]]),
                    tax_depreciation=_to_int(row[idx["tax depreciation"]]),
                    closing_cost=_to_int(row[idx["closing cost"]]),
                    closing_accum_depreciation=_to_int(row[idx["closing accumulated depreciation"]]),
                    closing_wdv=_to_int(row[idx["closing wdv"]]),
                )
                records_to_create.append(rec)
        except ValueError as ve:
            return render(request, "upload.html", {"form": form, "error": f"Row {row_num}: {ve}"})
        except Exception as e:
            return render(request, "upload.html", {"form": form, "error": f"Unexpected error on row {row_num}: {e}"})

        if records_to_create:
            TfarRecord.objects.bulk_create(records_to_create, batch_size=1000)

        # audit trail: insert one TfarUpload record
        TfarUpload.objects.create(
            client=client,
            uploaded_by=request.user,
            original_filename=uploaded.name,
            row_count=len(records_to_create),
            source_ip=_get_ip(request),
            checksum=checksum,
        )

        request.session["selected_client_id"] = str(client.id)
        return redirect("dashboard")

    # GET
    return render(request, "upload.html", {"form": UploadForm(user=request.user)})


# ------------- Download -------------

@login_required
def download_tfar_csv(request):
    selected_client_id = request.session.get("selected_client_id")
    if not selected_client_id:
        return HttpResponse("No client selected", status=400)

    client = get_object_or_404(Client, id=selected_client_id)
    membership = ClientMembership.objects.filter(user=request.user, client=client).first()
    if not membership:
        return HttpResponse("Forbidden", status=403)

    # PERMISSIONS: export ALL records that belong to this client
    qs = TfarRecord.objects.filter(client=client).order_by("asset_id")
    filename = f"{client.name}_tfar_export.csv"

    out = io.StringIO()
    out.write(",".join(["client"] + REQUIRED_HEADERS) + "\n")
    for r in qs:
        out.write(",".join([
            client.name,
            r.asset_id, r.asset_description, r.tax_start_date.isoformat(), r.depreciation_method,
            str(r.purchase_cost), str(r.tax_effective_life), str(r.opening_cost),
            str(r.opening_accum_depreciation), str(r.opening_wdv), str(r.addition),
            str(r.disposal), str(r.tax_depreciation), str(r.closing_cost),
            str(r.closing_accum_depreciation), str(r.closing_wdv),
        ]) + "\n")

    # audit trail: log the export
    TfarExport.objects.create(
        client=client, exported_by=request.user, filename=filename, row_count=qs.count()
    )

    response = HttpResponse(out.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# -------- Diagnostics (optional) --------
from django.conf import settings
import json

def env_view(request):
    data = {
        "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
        "CSRF_TRUSTED_ORIGINS": settings.CSRF_TRUSTED_ORIGINS,
        "DEBUG": getattr(settings, "DEBUG", None),
    }
    return HttpResponse(json.dumps(data, indent=2), content_type="application/json")

def safe_debug(request):
    try:
        rows = TfarRecord.objects.filter(client__isnull=False)[:1]
        return HttpResponse("Dashboard query OK, count=" + str(rows.count()))
    except Exception as e:
        import traceback
        return HttpResponse("<pre>" + str(e) + "\n\n" + traceback.format_exc() + "</pre>", content_type="text/plain")
