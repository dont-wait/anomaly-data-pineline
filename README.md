# Anomaly Data Pipeline

Repo sinh dữ liệu ngân hàng tổng hợp, liên kết theo khách hàng và phát thành event stream để thử nghiệm phát hiện giao dịch bất thường. Mimesis tạo dữ liệu nền; các scenario có seed tạo lịch sử tín dụng, khoản vay, giao dịch và nhãn đánh giá.

## Bắt đầu nhanh

Cần Nix có hỗ trợ flakes. Vào dev shell, cài dependency Python và frontend theo lockfile, rồi sinh dataset và báo cáo:

```bash
nix develop
make setup
make ui-install
make pipeline
make ui-dev
```

`make pipeline` chạy lần lượt `generate` và `report`, đồng thời copy `dashboard.json` và CSV vào `client/public/` để Vite phục vụ cho giao diện. Mở URL Vite được in ra terminal để xem dashboard. Dữ liệu JSONL được ghi vào `data/generated/`; báo cáo Markdown, CSV và JSON được ghi vào `reports/`.

Nếu không muốn mở shell tương tác:

```bash
nix develop --command make setup
nix develop --command make ui-install
nix develop --command make pipeline
nix develop --command make ui-dev
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
| `make ui-install` | Cài React/Vite dependencies theo `client/package-lock.json` |
| `make ui-dev` | Mở dashboard Vite ở `http://127.0.0.1:5173` |
| `make ui-build` | Build dashboard tĩnh vào `client/dist/` |

Có thể thay cấu hình và số lượng dữ liệu bằng Make variables:

```bash
make generate SEED=42 CUSTOMERS=1000 OUTPUT=data/run-42
make report OUTPUT=data/run-42 REPORT_DIR=reports/run-42
make pipeline SEED=42 CUSTOMERS=1000 OUTPUT=data/run-42 REPORT_DIR=reports/run-42
```

`make pipeline` nhận cùng các Make variables và truyền chúng cho cả hai bước generate/report.
Có thể chọn pipeline stage TOML khác bằng `PIPELINE=configs/pipeline.toml`.

Lệnh CLI tương đương:

```bash
uv run anomaly-data generate-data --config configs/base.yaml --pipeline configs/pipeline.toml --seed 42 --customers 1000 --output data/run-42
uv run anomaly-data report --data data/run-42 --output reports/run-42
```

## Cấu hình sinh dữ liệu

Cấu hình mặc định ở [configs/base.yaml](configs/base.yaml):

| Trường | Mặc định | Ý nghĩa |
|---|---:|---|
| `seed` | `20261002` | Seed cho Mimesis và các quyết định ngẫu nhiên |
| `customers` | `1000` | Số khách hàng/tài khoản được sinh |
| `transactions_per_customer` | `500` | Ngân sách giao dịch trung bình mỗi khách hàng; tổng = customers × giá trị này |
| `anomaly_rate` | `0.02` | Tỷ lệ mục tiêu phân bổ contextual scenarios; warmup và budget có thể ảnh hưởng số nhãn thực tế |
| `start_at` | `2025-01-01T00:00:00+07:00` | Thời điểm bắt đầu mô phỏng |
| `days` | `181` | Độ dài mô phỏng; mặc định bao trọn tháng 1 đến hết tháng 6/2025 |
| `output_dir` | `data/generated` | Thư mục JSONL và manifest |
| `campaign_days` | Ngày đôi trong năm | Hệ số tăng trọng số chọn ngày sale; ví dụ 5/5, 6/6 |

Lịch lễ mặc định là profile demo Việt Nam năm 2025. Payday, ngày đôi, cuối tháng, Tết và ngày lễ làm thay đổi xác suất chọn ngày phát sinh giao dịch. Các hệ số là giả định mô phỏng để tạo biến động có kiểm soát, không phải mức tăng được đo từ ngân hàng/nhà bán lẻ. Lịch nghỉ 2025 dựa trên [thông báo lịch nghỉ của Chính phủ](https://xaydungchinhsach.chinhphu.vn/lich-nghi-tet-nguyen-dan-at-ty-2025-119241127052424956.htm).

Tổng ngân sách giao dịch cố định được phân bổ khác nhau theo activity profile; mức chênh giữa các tháng đến từ độ dài tháng và việc dồn giao dịch vào các ngày có trọng số cao; tổng giao dịch toàn kỳ không tăng do sale. Seed giống nhau cùng cấu hình sẽ tái lập dữ liệu.

Mặc định tạo **1.000 khách hàng × 500 giao dịch = 500.000 giao dịch** trong 181 ngày. Số lifecycle event lớn hơn số giao dịch vì mỗi giao dịch có event yêu cầu và event kết quả. Tỷ lệ anomaly 2% là mục tiêu của bộ lập lịch scenario; số thực tế được báo trong labels/manifest, có thể khác do làm tròn hoặc budget cho warmup.

## Output

Mặc định generator tạo:

| File | Nội dung |
|---|---|
| `customers.jsonl` | Hồ sơ khách hàng, nhân khẩu tổng hợp, KYC và credit profile |
| `accounts.jsonl` | Tài khoản và số dư đầu kỳ |
| `loan_packages.jsonl` | Danh mục gói vay |
| `loan_applications.jsonl` | Yêu cầu vay, kỳ hạn, đánh giá và trạng thái |
| `loans.jsonl` | Khoản vay được duyệt, dư nợ, lãi suất, kỳ hạn |
| `transactions.jsonl` | Snapshot kết quả giao dịch với thời gian, loại, kênh, số tiền, fee và calendar context |
| `behavior_profiles.jsonl` | Metadata audit của generator (giờ/channel ưa thích, thu nhập, typical amount); không dùng làm oracle feature |
| `counterparties.jsonl` | Merchant và điểm cash dùng chung, làm node ngoài account |
| `transfer_events.jsonl` | Lifecycle transfer theo contract camelCase của Anomaly, schema version 1 |
| `events.jsonl` | Event bất biến, đã sắp theo `occurred_at` để replay |
| `labels.jsonl` | Ground-truth labels dành cho đánh giá offline |
| `manifest.json` | Seed, kỳ mô phỏng, nguồn profile và số dòng mỗi file |

Không đưa ground-truth label vào event payload đầu vào detector. Giao dịch ghi nợ vượt số dư được ghi trạng thái `failed`, bất kể nhãn anomaly. Các yêu cầu này vẫn nằm trong tập để đánh giá. `posted_at` là null nếu thất bại; `risk` không được sinh sẵn.

## Báo cáo

`make report` đọc JSONL hiện tại và tạo:

- `reports/dataset-analysis.md`: range số và phân bố category, tổng lượng dữ liệu, anomaly rate, lưu lượng theo tháng, chênh lệch ngày sale/lễ so với ngày thường.
- `reports/monthly-traffic.csv`: số giao dịch, trung bình/ngày, tổng giá trị VND và thay đổi so với tháng trước.
- `reports/dashboard.json`: dữ liệu có cấu trúc mà dashboard React đọc.

Dashboard nằm trong `client/`. Sau khi chạy `make pipeline`, dùng `make ui-dev` để xem biểu đồ lưu lượng theo tháng, chọn tháng để đổi KPI, xem loại giao dịch, ngày sale/lễ và tìm trường trong bảng min–max. Nút **Tải CSV** tải dữ liệu lưu lượng tháng.

Các kết quả trong report phụ thuộc seed và cấu hình. Chênh lệch của một seed cho biết generator đã phân bổ dữ liệu ra sao, không chứng minh ngày lễ/sale ngoài đời làm giao dịch tăng tương ứng.

## Cấu trúc source

```text
src/anomaly_data_pipeline/
├── cli.py                  # Lệnh generate-data và report
├── config.py               # Load và validate YAML config
├── domain/models.py        # Customer, Account, Transaction, Event
├── generation/
│   ├── calendar.py         # Lịch lễ/campaign và trọng số chọn ngày
│   ├── pipeline.py         # Khởi tạo context, load và chạy stages theo TOML
│   └── stages/             # Một module cho mỗi phần xử lý pipeline
│       ├── reference_data.py
│       ├── customer_accounts.py
│       ├── credit_history.py
│       ├── loan_lifecycle.py
│       ├── transactions.py
│       └── event_ordering.py
└── analysis.py             # Range fields, monthly traffic và ngày đặc biệt
```

`configs/pipeline.toml` quyết định thứ tự chạy stage, module xử lý, file output và options nghiệp vụ như gói vay, loại giao dịch, kênh, ngưỡng duyệt vay. Mỗi stage export `run(context, options)`; thêm bước bằng module riêng rồi khai báo entry `[[stages]]` trong TOML. Stage tạo dữ liệu cần đặt trước stage sử dụng dữ liệu đó. `configs/base.yaml` vẫn chứa tham số run như seed, số khách hàng, số ngày và anomaly rate. Chọn file khác bằng `make pipeline PIPELINE=configs/my-pipeline.toml`.

`flake.nix` cung cấp Python 3.13, Node.js 22, `uv` và `make`; `flake.lock` khóa phiên bản Nixpkgs. `uv.lock` và `client/package-lock.json` khóa dependency Python/JavaScript. Mimesis locale EN tạo tên/email/địa chỉ nền; province, nghề nghiệp, tuổi, thu nhập và quy tắc nghiệp vụ dùng vocabularies của generator nên chưa đại diện cho phân phối nhân khẩu Việt Nam thực tế.

## Phạm vi hiện tại

PaySim là nguồn tham khảo profile giao dịch, không được tải hay nhập trực tiếp. Generator có contextual_amount, velocity_burst, graph_fan_in và rapid_forwarding; chưa có account takeover, structuring hay bất thường dựa trên lịch trả nợ. Output là JSONL phục vụ phát triển và phân tích, chưa có MongoDB sink hoặc consumer replay nối vào detector.

## Dữ liệu train và event lifecycle (dataset schema 2)

Thời điểm chấm điểm được chọn là yêu cầu giao dịch, trước khi cập nhật số dư.

- Transfer: `TransferCreated` (sequence 1, `awaiting_otp`) → `TransferCompleted` (`success`) hoặc `TransferCancelled` (`cancelled`) (sequence 2).
- Nghiệp vụ khác: `TransactionRequested` (sequence 1, `requested`) → `TransactionPosted` (`success`) hoặc `TransactionRejected` (`failed`) (sequence 2).
- Sequence tăng trong từng transaction aggregate. Label `event_id` trỏ vào event yêu cầu; một transaction có một label dù có hai lifecycle events.
- `events.jsonl` giữ envelope snake_case chung cho các domain. Payload giao dịch dùng các field camelCase của Anomaly; nghiệp vụ ngoài transfer có thêm `transactionType`.
- `transfer_events.jsonl` chỉ chứa transfer, dùng đúng envelope `eventId`, `transactionId`, `eventType`, `schemaVersion`, `sequence`, `occurredAt`, `payload` của Anomaly. Event ID dùng UUID SHA1 namespace OID theo `transactionId:eventType`, giống backend.
- Request payload chỉ gồm source/destination, amount, fee, currency, channel và trạng thái yêu cầu. Balance trước/sau nằm ở event kết quả; không có risk, nhãn hay snapshot kết quả trong request.

Loader train lấy giao dịch cần chấm từ event yêu cầu, join label bằng transaction ID; không dùng snapshot kết quả trong `transactions.jsonl` làm feature trực tiếp. Không đưa `scenario_id`, status kết quả hoặc balance sau giao dịch vào model. Tách dữ liệu theo thời gian; chỉ cập nhật lịch sử/graph khi event tương ứng đã xảy ra.

Mọi thời điểm giao dịch được chọn trước và xử lý theo thứ tự thời gian toàn cục. Transfer thành công trừ amount + fee ở nguồn và cộng amount vào đích; thất bại không đổi số dư. Account snapshot giữ số dư đầu kỳ. Cash-in tăng số dư nguồn; cash-out/payment/debit giảm số dư nguồn và dùng node đối tác chung. Chuyển khoản chọn account đã tồn tại, ưu tiên nhóm người nhận quen; cần ít nhất hai account nếu bật TRANSFER. Các nhóm node ngoài account được ghi vào `counterparties.jsonl`.

Thông số người nhận, merchant/cash pool, fee, mức amount điển hình, multiplier và xác suất giao dịch lớn hợp lệ ở options của stage transactions trong TOML. Ground truth vẫn là kịch bản tổng hợp có kiểm soát, không chứng minh gian lận thực tế. Anomaly amount-outlier có thể xuất hiện ở nhiều loại giao dịch, không gắn cố định với CASH_OUT.

Đây là lifecycle tối thiểu: chưa sinh OTP resend/expiry (`TransferOTPUpdated`), chưa mô phỏng độ trễ xử lý (request và kết quả cùng timestamp, phân biệt bằng sequence), chưa nối balance của loan events vào ledger giao dịch. ID account tổng hợp cần mapping khi nhập vào tài khoản thật của Anomaly; contract tương thích không đồng nghĩa đã replay thành công vào backend.

Kiểm tra hồi quy không cần cài pytest:

```bash
nix develop
.venv/bin/python -m unittest discover -s tests -v
```

Bộ kiểm tra xác nhận replay balance toàn cục, contract transfer, label join, người nhận dùng chung, amount chồng lấn, kết quả tái lập theo seed và report chạy với schema mới. Dữ liệu/report cũ không tự được chuyển đổi; chạy lại `make pipeline` để tạo schema 2 và cập nhật dashboard.


## Contextual scenarios v3

Contract dataset/event vẫn là schema 2, native transfer schema 1. Manifest thêm `scenario_profile=contextual-v3`, snapshot generation/pipeline config và output behavior profiles để phân biệt cách dựng dữ liệu với bộ amount-only cũ.

Tổng mặc định vẫn 500.000 giao dịch nhưng mỗi account có số lượng khác nhau theo activity weight. Typical amount gắn với thu nhập và tần suất; customer có giờ/channel/receiver ưa thích. CASH_IN định kỳ theo payday là lifecycle giao dịch thật, nằm trong tổng budget. Cash-in bổ sung là nguồn tiền bên ngoài hệ thống được mô phỏng, không phải dòng tiền suy ra từ loan. Ledger loan vẫn riêng và không đưa vào feature.

- `contextual_amount`: amount lớn tương đối, giờ ngoài khung thường và channel ít dùng, ưu tiên receiver chưa gặp. Giao dịch lớn hợp lệ giữ giờ/channel/đối tác theo profile nên không phải cùng phân bố có nhãn ngẫu nhiên.
- `velocity_burst`: các request dồn trong thời gian ngắn; hai request đầu là warmup normal, positive chỉ sau khi đã có hai request trước trong 120 giây.
- `graph_fan_in`: nhiều account chuyển vào một hub; ba nguồn đầu là warmup normal, positive chỉ sau khi có ít nhất ba nguồn khác nhau trước đó trong 600 giây.
- `rapid_forwarding`: hub gửi tiếp sau fan-in đã quan sát. Dấu hiệu dùng transfer attempts; không mặc định tất cả chuyển khoản đều hoàn tất.

Tên scenario/nhãn chỉ ở sidecar. Không đưa profile generation, scenario marker, label hoặc kết quả xử lý vào request payload. Profile preferences của detector phải học từ lịch sử đã quan sát; không đọc oracle `behavior_profiles.jsonl`. Đây vẫn là mô phỏng theo giả định; rule được thiết kế theo scenario không phải benchmark thực tế hoặc bằng chứng GATv2 hiệu quả.

Các tham số activity, giờ/channel, income/spending, amount và scenario timing/weights nằm trong options của transactions stage ở TOML. Income và scenario slots tiêu thụ ngân sách tổng; giữ warmup là normal để nhãn không cần nhìn tương lai. Ở quy mô quá nhỏ, một số scenario không đủ actor/budget.
