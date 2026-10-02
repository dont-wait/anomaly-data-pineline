# Anomaly Data Pipeline

Repo sinh dữ liệu ngân hàng tổng hợp, liên kết theo khách hàng và phát thành event stream để thử nghiệm phát hiện giao dịch bất thường. Mimesis tạo dữ liệu nền; các scenario có seed tạo lịch sử tín dụng, khoản vay, giao dịch và nhãn đánh giá.

## Bắt đầu nhanh

Cần Nix có hỗ trợ flakes. Vào dev shell, cài dependency theo lockfile, rồi sinh dataset và báo cáo:

```bash
nix develop
make setup
make pipeline
```

`make pipeline` chạy lần lượt `generate` và `report`. Dữ liệu JSONL được ghi vào `data/generated/`; hai báo cáo được ghi vào `reports/`.

Nếu không muốn mở shell tương tác:

```bash
nix develop --command make setup
nix develop --command make pipeline
```

## Các lệnh Make

Chạy `make help` để xem danh sách. Những target thường dùng:

| Lệnh | Tác dụng |
|---|---|
| `make setup` | Cài dependency Python theo `uv.lock` |
| `make generate` | Sinh entity và event JSONL |
| `make report` | Tạo báo cáo Markdown và CSV từ dataset hiện có |
| `make pipeline` | Sinh dataset rồi cập nhật báo cáo |
| `make shell` | Mở Nix dev shell |
| `make clean` | Xóa thư mục output của dataset và báo cáo |

Có thể thay cấu hình và số lượng dữ liệu bằng Make variables:

```bash
make generate SEED=42 CUSTOMERS=1000 OUTPUT=data/run-42
make report OUTPUT=data/run-42 REPORT_DIR=reports/run-42
make pipeline SEED=42 CUSTOMERS=1000 OUTPUT=data/run-42 REPORT_DIR=reports/run-42
```

`make pipeline` nhận cùng các Make variables và truyền chúng cho cả hai bước generate/report.

Lệnh CLI tương đương:

```bash
uv run anomaly-data generate-data --config configs/base.yaml --seed 42 --customers 1000 --output data/run-42
uv run anomaly-data report --data data/run-42 --output reports/run-42
```

## Cấu hình sinh dữ liệu

Cấu hình mặc định ở [configs/base.yaml](configs/base.yaml):

| Trường | Mặc định | Ý nghĩa |
|---|---:|---|
| `seed` | `20261002` | Seed cho Mimesis và các quyết định ngẫu nhiên |
| `customers` | `100` | Số khách hàng/tài khoản được sinh |
| `transactions_per_customer` | `25` | Số giao dịch mỗi khách hàng |
| `anomaly_rate` | `0.02` | Xác suất gắn nhãn scenario bất thường cho mỗi giao dịch |
| `start_at` | `2025-01-01T00:00:00+07:00` | Thời điểm bắt đầu mô phỏng |
| `days` | `181` | Độ dài mô phỏng; mặc định bao trọn tháng 1 đến hết tháng 6/2025 |
| `output_dir` | `data/generated` | Thư mục JSONL và manifest |
| `campaign_days` | Ngày đôi trong năm | Hệ số tăng trọng số chọn ngày sale; ví dụ 5/5, 6/6 |

Lịch lễ mặc định là profile demo Việt Nam năm 2025. Payday, ngày đôi, cuối tháng, Tết và ngày lễ làm thay đổi xác suất chọn ngày phát sinh giao dịch. Các hệ số là giả định mô phỏng để tạo biến động có kiểm soát, không phải mức tăng được đo từ ngân hàng/nhà bán lẻ. Lịch nghỉ 2025 dựa trên [thông báo lịch nghỉ của Chính phủ](https://xaydungchinhsach.chinhphu.vn/lich-nghi-tet-nguyen-dan-at-ty-2025-119241127052424956.htm).

Vì mỗi khách hàng được sinh số lượng giao dịch cố định trong toàn kỳ, mức chênh giữa các tháng đến từ độ dài tháng và việc dồn giao dịch vào các ngày có trọng số cao; tổng giao dịch toàn kỳ không tăng do sale. Seed giống nhau cùng cấu hình sẽ tái lập dữ liệu.

## Output

Mặc định generator tạo:

| File | Nội dung |
|---|---|
| `customers.jsonl` | Hồ sơ khách hàng, nhân khẩu tổng hợp, KYC và credit profile |
| `accounts.jsonl` | Tài khoản và số dư đầu kỳ |
| `loan_packages.jsonl` | Danh mục gói vay |
| `loan_applications.jsonl` | Yêu cầu vay, kỳ hạn, đánh giá và trạng thái |
| `loans.jsonl` | Khoản vay được duyệt, dư nợ, lãi suất, kỳ hạn |
| `transactions.jsonl` | Giao dịch với thời gian, loại, kênh, số tiền, risk và calendar context |
| `events.jsonl` | Event bất biến, đã sắp theo `occurred_at` để replay |
| `labels.jsonl` | Ground-truth labels dành cho đánh giá offline |
| `manifest.json` | Seed, kỳ mô phỏng, nguồn profile và số dòng mỗi file |

Không đưa ground-truth label vào event payload đầu vào detector. Giao dịch cash-out bất thường vượt số dư được ghi trạng thái `failed` và phát event từ chối; các giao dịch này vẫn nằm trong tập để đánh giá phát hiện hành vi đáng ngờ.

## Báo cáo

`make report` đọc JSONL hiện tại và tạo:

- `reports/dataset-analysis.md`: range số và phân bố category, tổng lượng dữ liệu, anomaly rate, lưu lượng theo tháng, chênh lệch ngày sale/lễ so với ngày thường.
- `reports/monthly-traffic.csv`: số giao dịch, trung bình/ngày, tổng giá trị VND và thay đổi so với tháng trước.

Các kết quả trong report phụ thuộc seed và cấu hình. Chênh lệch của một seed cho biết generator đã phân bổ dữ liệu ra sao, không chứng minh ngày lễ/sale ngoài đời làm giao dịch tăng tương ứng.

## Cấu trúc source

```text
src/anomaly_data_pipeline/
├── cli.py                  # Lệnh generate-data và report
├── config.py               # Load và validate YAML config
├── domain/models.py        # Customer, Account, Transaction, Event
├── generation/
│   ├── calendar.py         # Lịch lễ/campaign và trọng số chọn ngày
│   └── pipeline.py         # Sinh entity, scenario và chronological event stream
└── analysis.py             # Range fields, monthly traffic và ngày đặc biệt
```

`flake.nix` cung cấp Python 3.13, `uv` và `make`; `flake.lock` khóa phiên bản Nixpkgs. `uv.lock` khóa dependency Python. Mimesis locale EN tạo tên/email/địa chỉ nền; province, nghề nghiệp, tuổi, thu nhập và quy tắc nghiệp vụ dùng vocabularies của generator nên chưa đại diện cho phân phối nhân khẩu Việt Nam thực tế.

## Phạm vi hiện tại

PaySim là nguồn tham khảo profile giao dịch, không được tải hay nhập trực tiếp. Generator hiện tạo kịch bản amount-outlier; chưa có velocity, account takeover, structuring hay bất thường dựa trên lịch trả nợ. Output là JSONL phục vụ phát triển và phân tích, chưa có MongoDB sink hoặc consumer replay nối vào detector.
