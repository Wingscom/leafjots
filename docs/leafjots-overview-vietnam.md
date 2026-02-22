# LeafJots -- Thị Trường Việt Nam

> Tài liệu bổ sung cho đội kinh doanh khi tiếp cận khách hàng tại Việt Nam.
> Đọc kèm với [leafjots-overview-global.md](leafjots-overview-global.md).

---

## 1. Bối Cảnh Pháp Lý Việt Nam

### Luật Công nghệ số (Luật 71/2025/QH15)

Luật này chính thức quy định tài sản số là đối tượng chịu thuế tại Việt Nam.
Các điểm chính:

| Nội dung | Chi tiết |
|----------|----------|
| Thuế suất | **0.1%** trên giá trị chuyển nhượng mỗi lần |
| Miễn thuế | Giao dịch đơn lẻ **dưới 20 triệu VND** (~800 USD) được miễn |
| Phương pháp tính giá vốn | **FIFO bắt buộc** (nhập trước xuất trước) |
| Hạn khai thuế | Tự khai hàng năm, deadline **31/03** năm sau |
| Đơn vị tiền | Báo cáo **song ngữ: USD + VND** |
| Ai phải khai | Cá nhân và tổ chức có giao dịch chuyển nhượng tài sản số |

### Tại sao DeFi là trọng tâm tại VN?

| Kênh giao dịch | Thuế thế nào? | LeafJots cần không? |
|----------------|---------------|---------------------|
| **Sàn nội địa** (VNDirect, SSI...) | Sàn tự thu thuế 0.1% thay người dùng | Không cần tool |
| **Sàn ngoại** (Binance, OKX...) | Chưa rõ comply, người dùng tự khai | Cần (import CSV) |
| **DeFi** (Uniswap, Aave...) | **Không ai thu thuế thay** | **BẮT BUỘC cần tool** |

Người dùng DeFi giao dịch trực tiếp trên blockchain, không qua trung gian. Họ phải
tự theo dõi, tự ghi sổ, tự tính thuế. LeafJots giải quyết đúng bài toán này.

---

## 2. LeafJots Xử Lý Thuế VN Như Thế Nào?

### Thuế 0.1% chuyển nhượng

Mỗi lần **chuyển nhượng** tài sản số (bán, swap, chuyển...), thuế = 0.1% giá trị.

```
Ví dụ: Swap 1 ETH (giá 60 triệu VND) lấy 2,500 USDC

  Giá trị chuyển nhượng  : 60,000,000 VND
  Thuế 0.1%              : 60,000 VND
```

### Miễn thuế giao dịch nhỏ

Giao dịch đơn lẻ **dưới 20 triệu VND** (~800 USD) được miễn. LeafJots tự động
kiểm tra và đánh dấu:

```
  TX 1: Swap 0.2 ETH (12 triệu VND)   → MIỄN THUẾ (< 20M VND)
  TX 2: Swap 1 ETH (60 triệu VND)     → CHỊU THUẾ: 60,000 VND
  TX 3: Swap 0.1 ETH (6 triệu VND)    → MIỄN THUẾ (< 20M VND)
```

### FIFO bắt buộc

Việt Nam bắt buộc phương pháp FIFO. LeafJots dùng **Global FIFO** -- gộp tất cả
ví của 1 entity thành 1 hàng đợi chung:

```
  Mua 1 ETH giá 40M VND (tháng 1)
  Mua 1 ETH giá 50M VND (tháng 3)
  Bán 1 ETH giá 60M VND (tháng 6)

  FIFO: bán lô mua tháng 1 trước
  → Giá vốn = 40M VND
  → Lãi thực hiện = 60M - 40M = 20M VND
```

### Báo cáo song ngữ USD + VND

Mọi giá trị trong báo cáo đều có **2 cột**: USD và VND. Tỷ giá quy đổi tại thời
điểm giao dịch.

---

## 3. Lợi Thế So Với Tool Quốc Tế (Tại Thị Trường VN)

| Đặc điểm | LeafJots | Koinly / CoinTracker |
|-----------|----------|---------------------|
| Luật thuế VN | Đúng luật 71/2025 (0.1%, FIFO, VND 20M) | Không hỗ trợ VN |
| Thuế 0.1% transfer | Tính chính xác từng giao dịch | Không có rule này |
| Miễn thuế 20M VND | Tự động loại trừ | Không biết rule này |
| Báo cáo VND | Song ngữ USD + VND | Chỉ USD/EUR |
| FIFO bắt buộc | Global FIFO đúng chuẩn VN | Có FIFO nhưng không bắt buộc |
| Dữ liệu | Chạy local, dữ liệu tại VN | Cloud nước ngoài |

**Kết luận:** Tool quốc tế **không thể** tạo báo cáo thuế hợp lệ cho VN.
Nộp thuế theo Koinly = sai rule = rủi ro pháp lý.

---

## 4. Khách Hàng Mục Tiêu Tại VN

### Nhóm 1: Cá nhân DeFi (ưu tiên cao nhất)

- Dùng Uniswap, Aave, Curve, Lido, Pendle...
- Hàng trăm đến hàng ngàn giao dịch/năm
- Không biết cách tính thuế, sợ rủi ro pháp lý
- **Pain point:** "Tôi biết phải khai thuế nhưng không biết tính thế nào"

### Nhóm 2: Quỹ crypto / DAO

- Quản lý nhiều ví, nhiều chain
- Cần báo cáo cho LP, cơ quan thuế
- Cần multi-entity (mỗi quỹ = 1 entity)
- **Pain point:** "Cần báo cáo chuẩn kế toán cho investor"

### Nhóm 3: Người dùng Binance

- Giao dịch spot, futures, earn trên Binance
- Binance không thu thuế thay VN
- Upload CSV là xong
- **Pain point:** "Binance không cho tôi báo cáo thuế VN"

### Nhóm 4: Kế toán viên / Văn phòng kế toán

- Nhận outsource khai thuế crypto cho khách hàng
- Quản lý 10-50 khách, mỗi khách 1 entity
- **Pain point:** "Không có tool nào hỗ trợ luật VN để tôi làm cho khách"

---

## 5. FAQ Riêng Cho Thị Trường VN

### "Tại sao tôi cần khai thuế crypto?"

Luật 71/2025/QH15 quy định mọi giao dịch chuyển nhượng tài sản số đều phải khai
thuế 0.1%. Không khai = vi phạm luật thuế.

### "Sàn Binance đã trừ thuế cho tôi rồi mà?"

Sai. Binance là sàn nước ngoài, **không** thu thuế thay cho VN. Bạn vẫn phải tự khai.
Chỉ sàn nội địa VN (nếu có) mới thu hộ.

### "Giao dịch nhỏ có phải khai không?"

Giao dịch **dưới 20 triệu VND** được miễn thuế. Nhưng vẫn nên ghi nhận để chứng minh
khi cơ quan thuế yêu cầu. LeafJots tự động đánh dấu giao dịch miễn thuế.

### "Tôi chỉ hold Bitcoin thôi, không bán, có phải khai không?"

Hold không bán = không chuyển nhượng = **không phải khai thuế**. Chỉ khi nào bán,
swap, hay chuyển mới phát sinh thuế.

### "Deadline khai thuế là khi nào?"

**31/03 hàng năm** cho năm tài chính trước. Ví dụ: giao dịch năm 2026 → khai trước
31/03/2027.

### "Tool quốc tế như Koinly không dùng được à?"

Koinly không hiểu luật VN: không có rule 0.1%, không miễn thuế 20M VND, không báo
cáo VND. Dùng Koinly nộp thuế VN = **sai**.

### "Dữ liệu có ra nước ngoài không?"

Không. LeafJots chạy local trên máy. Không upload dữ liệu lên server nào.

### "Nếu tôi giao dịch trên nhiều chain thì sao?"

LeafJots hỗ trợ Ethereum + Solana. Sắp tới thêm Arbitrum, Polygon, BSC. Tất cả ví
gộp vào 1 entity, tính FIFO chung.

---

## 6. Kịch Bản Demo Cho Khách VN

### Mở đầu (2 phút)

- Giới thiệu luật 71/2025: "Anh/chị có biết từ năm nay phải khai thuế crypto?"
- Nêu vấn đề: "DeFi không ai thu thuế hộ, tự khai rất phức tạp"
- Giới thiệu LeafJots: "Tool duy nhất hỗ trợ đúng luật thuế VN"

### Demo live (5-8 phút)

1. Tạo entity cho khách demo
2. Thêm ví Ethereum → Sync → xem TX tải về
3. Show parser tự nhận diện swap, deposit, gas
4. Show journal kế toán kép -- mọi entry cân bằng
5. Chạy Tax Calculator:
   - Show lãi/lỗ FIFO
   - Show thuế 0.1% từng giao dịch
   - Show giao dịch được miễn (< 20M VND)
   - Show tổng thuế phải nộp
6. Xuất Excel → mở file → show sheet tax_summary + balance_sheet VND

### Nếu khách dùng Binance

- Upload CSV → show 48 loại giao dịch được phân loại
- Show tổng hợp: bao nhiêu TX, bao nhiêu lỗi, thuế tổng

### Closing (1 phút)

- "Báo cáo này nộp thẳng cho cơ quan thuế, đúng format, đúng luật"
- "Dữ liệu chạy local, anh/chị toàn quyền"
- Next step: setup cho khách, import ví/CSV thật

---

## 7. Thuế VN vs Thuế Quốc Tế (So Sánh Nhanh)

| Quốc gia | Loại thuế | Thuế suất | Miễn thuế | Phương pháp |
|----------|-----------|-----------|-----------|-------------|
| **Việt Nam** | Transfer tax (0.1%) | 0.1% / giao dịch | < 20M VND | FIFO bắt buộc |
| Mỹ (US) | Capital gains | 0-37% tuỳ thu nhập | $0 (khai hết) | FIFO/LIFO/Specific ID |
| Anh (UK) | Capital gains | 10-20% | £3,000/năm | Share pooling |
| Đức | Capital gains | 0% nếu hold > 1 năm | €600/năm | FIFO |
| Singapore | Không thuế | 0% | N/A | N/A |
| Hồng Kông | Không thuế | 0% | N/A | N/A |

**Điểm khác biệt của VN:** Thuế VN là **transfer tax cố định 0.1%** (thuế trên mỗi
giao dịch), không phải capital gains tax (thuế trên lãi). Nghĩa là bán lỗ vẫn phải
đóng 0.1%.

Đây là điểm quan trọng khi nói với khách: "Dù bán lỗ vẫn phải đóng thuế 0.1%
trên giá trị chuyển nhượng."

---

*Tài liệu cập nhật: 2026-02-20*
*Đọc kèm: [leafjots-overview-global.md](leafjots-overview-global.md)*
