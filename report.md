1. Sinh dữ liệu trọn vòng đời khách hàng
- Mỗi khách hàng có hồ sơ, tài khoản, lịch sử tín dụng 6 tháng, đơn vay, khoản vay và chuỗi giao dịch.
- Mặc định mỗi lần chạy có 100 khách hàng, 2.500 giao dịch và khoảng 3.000 sự kiện, theo trình tự thời gian.
- Có sẵn 3 gói vay mẫu. Quyết định duyệt vay phụ thuộc điểm tín dụng và nợ xấu của từng khách.

2. Bối cảnh thực tế của Việt Nam
- Lịch mô phỏng 6 tháng đầu năm 2025 có Tết, các ngày lễ, ngày lĩnh lương, cuối tháng và các ngày sale đôi (5/5, 6/6, 11/11, 12/12).
- Các ngày này làm lượng giao dịch tăng giảm có kiểm soát. Các hệ số là giả định, không phải số đo từ ngân hàng thật.

3. Nhãn bất thường để đánh giá
- Khoảng 2% giao dịch được gắn nhãn bất thường (bản báo cáo hiện có: 47/2.500).
- Nhãn nằm ở file riêng để chấm điểm sau, không lẫn vào dữ liệu đưa cho bộ phát hiện.

4. Báo cáo phân tích và dashboard
- Một lệnh tạo báo cáo khối lượng dữ liệu, khoảng giá trị từng trường và lưu lượng giao dịch theo tháng.
- Có giao diện web (dashboard) hiển thị kết quả.
- Một lệnh duy nhất (make pipeline) chạy từ sinh dữ liệu đến báo cáo.
