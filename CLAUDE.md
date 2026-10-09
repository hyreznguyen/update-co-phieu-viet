# Sổ Cổ Phiếu Việt

Trang research cổ phiếu Việt Nam cá nhân của Anh, chạy trên GitHub Pages (trang tĩnh, không build).

## Cấu trúc
- `index.html` — toàn bộ trang (HTML/CSS/JS thuần). Đọc dữ liệu từ `data/`.
- `data/tickers.json` — danh sách mã hiển thị. Thêm mã mới thì phải thêm vào đây.
- `data/stocks/<MÃ>.json` — bản research của từng mã (câu chuyện, thesis, định giá, tài chính 5 năm, tin, rủi ro).
- `data/prices.json` — giá đóng cửa, do GitHub Actions ghi tự động. Không sửa tay trừ khi cần khởi tạo giá cho mã mới.
- `scripts/update_prices.py` + `.github/workflows/update-prices.yml` — lấy giá 16:15 giờ VN mỗi ngày giao dịch.

## Khi Anh nhờ research một mã
Viết `data/stocks/<MÃ>.json` theo đúng cấu trúc của `data/stocks/FPT.json` (mẫu chuẩn về văn phong), thêm mã vào `data/tickers.json`, thêm giá hiện tại vào `data/prices.json`, rồi commit và push lên `main`.

Trọng tâm: câu chuyện (`story`, `tagline`) và thesis (`thesis`, `thesisPoints[{title,detail}]`, `thesisBreakers[]`). Anh không muốn chấm điểm, không muốn phân tích kỹ thuật, tin tức không cần link.

Các trường số mà trang dùng để tự tính lại theo giá mới:
- `epsTTM` — EPS 12 tháng gần nhất (đồng), theo số cổ phiếu hiện tại
- `bvps` — giá trị sổ sách mỗi cổ phiếu (đồng)
- `sharesMn` — số cổ phiếu lưu hành (triệu)
- `dps` — cổ tức tiền mặt dự kiến mỗi cổ phiếu/năm (đồng)
- `intrinsic{low,base,high}` — giá trị nội tại (đồng/cp)

`metrics` chỉ chứa các chỉ số không phụ thuộc giá (roe, netMargin, debtEquity, epsGrowth, evEbitda...); P/E, P/B, tỷ suất cổ tức do trang tự tính.

`financials`: `unit`, `years` (5 năm + có thể thêm cột 12 tháng gần nhất), `cagrCols: 5`, `rows` gồm Doanh thu / LN trước thuế / LNST cổ đông mẹ / EPS điều chỉnh (đồng), `note`.

Mỗi lần research lại: nối thêm `{date, price, intrinsicBase, recommendation}` vào `history`.

Văn phong: tiếng Việt, giữ thuật ngữ tài chính tiếng Anh trong ngoặc khi hữu ích, góc nhìn đầu tư giá trị. Không bịa số; ghi rõ số nào là ước tính trong `financials.note`.
