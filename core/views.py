
import io
from typing import Any, List

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from .forms import UploadForm, ClientSelectForm
from .models import TfarRecord, Client, ClientMembership

REQUIRED_HEADERS: List[str] = [
    "asset id","asset description","tax start date","depreciation method",
    "purchase cost","tax effective life","opening cost",
    "opening accumulated depreciation","opening wdv",
    "addition","disposal","tax depreciation",
    "closing cost","closing accumulated depreciation","closing wdv",
]

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

def login_view(request):
    if request.method == "POST":
        u = request.POST.get("username"); p = request.POST.get("password")
        user = authenticate(request, username=u, password=p)
        if user: login(request, user); return redirect("dashboard")
        return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

def logout_view(request):
    logout(request); return redirect("login")

###TEMP - DELETE FOR PROD
import traceback

def safe_debug(request):
    try:
        # Force dashboard code
        rows = TfarRecord.objects.filter(owner=request.user)[:1]
        return HttpResponse("Dashboard query OK, count=" + str(rows.count()))
    except Exception as e:
        return HttpResponse(
            "<pre>" + str(e) + "\n\n" + traceback.format_exc() + "</pre>", 
            content_type="text/plain"
        )

def debug_view(request):
    raise Exception("Manual test exception — this should show a 500 if debug middleware isn’t interfering")

####TEMP ABOVE



@login_required
def dashboard(request):
    memberships = ClientMembership.objects.filter(user=request.user).select_related("client").order_by("client__name")

    if not memberships.exists():
        return render(
            request, 
            "dashboard.html",
            {
                "rows": [],
                "form": None,
                "client": None,
                "error": "You are not assigned to any clients. Please ask an administrator to add you."
            }
        )
    
    # Determine selected client (from POST or session), fallback to first membership
    selected_client_id = request.POST.get("client") or request.session.get("selected_client_id")
    #memberships = ClientMembership.objects.filter(user=request.user).select_related("client").order_by("client__name")
    #if not memberships.exists():
    #    return render(request, "dashboard.html", {
    #        "rows": [], "form": ClientSelectForm(user=request.user),
    #        "error": "No client memberships assigned. Ask an admin to add you to a client."
    #    })

    if not selected_client_id:
        selected_client_id = str(memberships.first().client.id)

    # Persist selection in session
    request.session["selected_client_id"] = selected_client_id

    client = get_object_or_404(Client, id=selected_client_id)
    # Guard: ensure user belongs to this client
    if not memberships.filter(client=client).exists():
        return render(request, "dashboard.html", {"rows": [], "form": ClientSelectForm(user=request.user),
                                                  "error": "You don't have access to this client."})

    rows = (TfarRecord.objects
            .filter(owner=request.user, client=client)
            .order_by("-uploaded_at", "asset_id")[:500])

    form = ClientSelectForm(user=request.user, data={"client": selected_client_id})
    return render(request, "dashboard.html", {"rows": rows, "form": form, "client": client})

@login_required
def upload_tfar(request):
    # Selected client comes from the form; choices restricted to memberships
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return render(request, "upload.html", {"form": form, "error": "Invalid submission"})

        uploaded = request.FILES.get("file"); client_id = form.cleaned_data["client"]
        if not uploaded or not uploaded.name.lower().endswith(".xlsx"):
            return render(request, "upload.html", {"form": form, "error": "Upload a .xlsx file"})

        client = get_object_or_404(Client, id=client_id)
        if not ClientMembership.objects.filter(user=request.user, client=client).exists():
            return render(request, "upload.html", {"form": form, "error": "You don't have access to this client"})

        try:
            wb = load_workbook(filename=uploaded, data_only=True); ws = wb.active
        except Exception as e:
            return render(request, "upload.html", {"form": form, "error": f"Failed to read Excel: {e}"})

        headers = [(_c.value or "").strip().lower() for _c in ws[1]]
        if len(headers) != 15 or headers != REQUIRED_HEADERS:
            return render(request, "upload.html", {"form": form,
                "error": "Column mismatch. Expected exactly: " + ", ".join(REQUIRED_HEADERS)})

        records_to_create: list[TfarRecord] = []
        row_num = 1
        try:
            for row in ws.iter_rows(min_row=2, values_only=True):
                row_num += 1
                if row is None or all(v is None or (isinstance(v, str) and v.strip() == "") for v in row):
                    continue
                rec = TfarRecord(
                    owner=request.user, client=client,
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
            return render(request, "upload.html", {"form": form, "error": f"Row {row_num}: {ve}"})
        except Exception as e:
            return render(request, "upload.html", {"form": form, "error": f"Unexpected error on row {row_num}: {e}"})

        if records_to_create:
            TfarRecord.objects.bulk_create(records_to_create, batch_size=1000)

        # After successful upload, remember the client in session and redirect to dashboard
        request.session["selected_client_id"] = str(client.id)
        return redirect("dashboard")

    # GET
    form = UploadForm(user=request.user)
    return render(request, "upload.html", {"form": form})

@login_required
def download_tfar_csv(request):
    selected_client_id = request.session.get("selected_client_id")
    if not selected_client_id:
        return HttpResponse("No client selected", status=400)

    client = get_object_or_404(Client, id=selected_client_id)
    if not ClientMembership.objects.filter(user=request.user, client=client).exists():
        return HttpResponse("Forbidden", status=403)

    qs = TfarRecord.objects.filter(owner=request.user, client=client).order_by("asset_id")
    out = io.StringIO()
    out.write(",".join(REQUIRED_HEADERS) + "\n")
    for r in qs:
        out.write(",".join([
            r.asset_id, r.asset_description, r.tax_start_date.isoformat(), r.depreciation_method,
            str(r.purchase_cost), str(r.tax_effective_life), str(r.opening_cost),
            str(r.opening_accum_depreciation), str(r.opening_wdv), str(r.addition),
            str(r.disposal), str(r.tax_depreciation), str(r.closing_cost),
            str(r.closing_accum_depreciation), str(r.closing_wdv),
        ]) + "\n")
    resp = HttpResponse(out.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{client.name}_tfar_export.csv"'
    return resp
