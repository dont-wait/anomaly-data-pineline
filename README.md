# Anomaly Data Pipeline

Pipeline tạo bộ dữ liệu ngân hàng tổng hợp có quan hệ và event stream để thử nghiệm phát hiện giao dịch bất thường. Dữ liệu cá nhân được tạo bằng Mimesis; seed điều khiển cả Mimesis và bộ sinh scenario để tái lập kết quả.

## Luồng dữ liệu

```text
Mimesis + seeded scenarios
  -> customers / credit history / accounts / loan applications and products
  -> transactions with customer and loan context
  -> append-only JSONL domain events
  -> offline labels sidecar for evaluation
```

Event đầu vào detector không chứa nhãn ground truth. Nhãn được ghi riêng vào `labels.jsonl`. `events.jsonl` là log bất biến để replay; các file entity riêng là snapshot tiện cho phân tích. Gói vay và lịch sử thanh toán hiện nằm trong payload event theo sơ đồ logic, có thể materialize thành collections ở bước sink tiếp theo.

PaySim là nguồn tham khảo phân phối hành vi giao dịch (`paysim-inspired`), không được tải hay trộn trực tiếp vào dữ liệu mặc định. Các loại giao dịch và mức bất thường hiện là profile mô phỏng có thể cấu hình; cần hiệu chỉnh với thống kê PaySim nếu muốn tái tạo sát dataset đó.

## Chạy

Yêu cầu Python 3.11+ và `uv`:

```bash
uv sync
uv run anomaly-data --config configs/base.yaml
```

Tuỳ chỉnh nhanh:

```bash
uv run anomaly-data --seed 42 --customers 1000 --output data/run-42
```

Lệnh ghi `customers.jsonl`, `accounts.jsonl`, `transactions.jsonl`, `events.jsonl`, `labels.jsonl` và `manifest.json` vào thư mục output. Dữ liệu sinh không được commit.

## Cấu trúc source

```text
src/anomaly_data_pipeline/
├── cli.py                 # CLI, không chứa nghiệp vụ sinh
├── config.py              # Parse và validate cấu hình
├── domain/models.py       # Model dữ liệu/events theo logical schema
└── generation/pipeline.py # Điều phối deterministic generation
```

## Các giới hạn hiện tại

- Mimesis locale EN tạo tên/email và địa chỉ nền; province, nghề nghiệp, tuổi, thu nhập cùng lịch sử tín dụng được kiểm soát bằng vocabularies và seeded rules. Đây là dữ liệu tổng hợp, không phải phân phối nhân khẩu Việt Nam đã được kiểm chứng.
- Anomaly scenarios hiện tập trung vào giao dịch cash-out số tiền lớn; cần bổ sung scenario velocity, account takeover, structuring và bất thường gắn lịch trả nợ trước khi dùng đánh giá mô hình nghiêm túc.
- Đây là source pipeline và JSONL sink đầu tiên. MongoDB writer, orchestration, model replay consumer và schema registry chưa được thêm.

