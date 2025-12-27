
import io, pandas as pd
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import UploadForm
from .models import TfarRecord

REQUIRED_HEADERS = [
    "asset id","asset description","tax start date","depreciation method",
    "purchase cost","tax effective life","opening cost",
    "opening accumulated depreciation","opening wdv",
    "addition","disposal","tax depreciation",
    "closing cost","closing accumulated depreciation","closing wdv",
]

def login_view(request):
    if request.method == "POST":
        u = request.POST.get("username"); p = request.POST.get("password")
        user = authenticate(request, username=u, password=p)
        if user: login(request, user); return redirect("dashboard")
        return render(request, "login.html", {"error": "Invalid credentials"})
    return render(request, "login.html")

def logout_view(request):
    logout(request); return redirect("login")

@login_required
def dashboard(request):
    rows = TfarRecord.objects.filter(owner=request.user).order_by("-uploaded_at")[:500]
    return render(request, "dashboard.html", {"rows": rows})

@login_required
def upload_tfar(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            if not f.name.lower().endswith(".xlsx"):
                return render(request, "upload.html", {"form": form, "error": "Please upload .xlsx files only."})
            df = pd.read_excel(f, engine="openpyxl")
            cols = [str(c).strip().lower() for c in df.columns]
            if len(cols) != 15 or cols != REQUIRED_HEADERS:
                return render(request, "upload.html", {"form": form,
                    "error": "Column mismatch. Expected exactly 15 headers:\n" + ", ".join(REQUIRED_HEADERS)})
            records = []
            for _, r in df.iterrows():
                try:
                    records.append(TfarRecord(
                        owner=request.user,
                        asset_id=str(r["asset id"])[:50],
                        asset_description=str(r["asset description"])[:250],
                        tax_start_date=pd.to_datetime(r["tax start date"]).date(),
                        depreciation_method=str(r["depreciation method"])[:50],
                        purchase_cost=int(r["purchase cost"]),
                        tax_effective_life=int(r["tax effective life"]),
                        opening_cost=int(r["opening cost"]),
                        opening_accum_depreciation=int(r["opening accumulated depreciation"]),
                        opening_wdv=int(r["opening wdv"]),
                        addition=int(r["addition"]),
                        disposal=int(r["disposal"]),
                        tax_depreciation=int(r["tax depreciation"]),
                        closing_cost=int(r["closing cost"]),
                        closing_accum_depreciation=int(r["closing accumulated depreciation"]),
                        closing_wdv=int(r["closing wdv"]),
                    ))
                except Exception as e:
                    return render(request, "upload.html", {"form": form, "error": f"Row parse error: {e}"})
            TfarRecord.objects.bulk_create(records, batch_size=1000)
            return redirect("dashboard")
    else:
        form = UploadForm()
    return render(request, "upload.html", {"form": form})

@login_required
def download_tfar_csv(request):
    qs = TfarRecord.objects.filter(owner=request.user).order_by("asset_id")
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
    resp["Content-Disposition"] = 'attachment; filename="tfar_export.csv"'
    return resp
