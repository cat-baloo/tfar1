
# core/views.py (top of file)
import io
from openpyxl import load_workbook
from django.contrib.auth import authenticate, login, logout
# ... keep the rest

# Replace the pandas-based branch in upload_tfar() with openpyxl:
@login_required
def upload_tfar(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = request.FILES["file"]
            if not f.name.lower().endswith(".xlsx"):
                return render(request, "upload.html", {"form": form, "error": "Please upload .xlsx files only."})

            # Read the first worksheet
            wb = load_workbook(filename=f, data_only=True)
            ws = wb.active

            # Extract header row (assume row 1)
            headers = [str(cell.value).strip().lower() if cell.value is not None else "" for cell in ws[1]]
            if len(headers) != 15 or headers != REQUIRED_HEADERS:
                return render(request, "upload.html", {"form": form,
                    "error": "Column mismatch. Expected exactly 15 headers:\n" + ", ".join(REQUIRED_HEADERS)})

            # Iterate remaining rows and build records
            records = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                try:
                    # Map by header index to keep exact ordering
                    def v(i): return row[i]  # convenience
                    records.append(TfarRecord(
                        owner=request.user,
                        asset_id=str(v(0))[:50],
                        asset_description=str(v(1))[:250],
                        tax_start_date=(v(2)).date() if hasattr(v(2), "date") else v(2),
                        depreciation_method=str(v(3))[:50],
                        purchase_cost=int(v(4) or 0),
                        tax_effective_life=int(v(5) or 0),
                        opening_cost=int(v(6) or 0),
                        opening_accum_depreciation=int(v(7) or 0),
                        opening_wdv=int(v(8) or 0),
                        addition=int(v(9) or 0),
                        disposal=int(v(10) or 0),
                        tax_depreciation=int(v(11) or 0),
                        closing_cost=int(v(12) or 0),
                        closing_accum_depreciation=int(v(13) or 0),
                        closing_wdv=int(v(14) or 0),
                    ))
                except Exception as e:
                    return render(request, "upload.html", {"form": form, "error": f"Row parse error: {e}"})
            TfarRecord.objects.bulk_create(records, batch_size=1000)
            return redirect("dashboard")
    else:
        form = UploadForm()
    return render(request, "upload.html", {"form": form})
