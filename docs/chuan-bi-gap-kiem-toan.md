# Chuẩn bị gặp Kiểm toán viên — LeafJots

> Tài liệu cho developer: hiểu nghiệp vụ kế toán trước buổi tư vấn.
> Mục tiêu: biết đủ để hỏi đúng câu, hiểu được câu trả lời.

---

## Mục lục

1. [Kế toán kép là gì?](#1-kế-toán-kép-double-entry-là-gì)
2. [4 loại tài khoản](#2-bốn-loại-tài-khoản)
3. [Bút toán (Journal Entry) và Splits](#3-bút-toán-journal-entry-và-splits)
4. [Ví dụ thực tế DeFi → Bút toán](#4-ví-dụ-thực-tế-defi--bút-toán)
5. [FIFO là gì?](#5-fifo-là-gì)
6. [Thuế Việt Nam — Luật 71/2025](#6-thuế-việt-nam--luật-712025)
7. [Sản phẩm LeafJots làm gì?](#7-sản-phẩm-leafjots-làm-gì)
8. [Câu hỏi cần hỏi kiểm toán viên](#8-câu-hỏi-cần-hỏi-kiểm-toán-viên)
9. [Thuật ngữ kế toán ↔ tiếng Việt](#9-thuật-ngữ-kế-toán--tiếng-việt)

---

## 1. Kế toán kép (Double-Entry) là gì?

### Ý tưởng cốt lõi

Mỗi giao dịch tài chính **luôn ảnh hưởng ít nhất 2 tài khoản**, và tổng phải bằng 0.

**Tại sao?** Tiền không tự sinh ra hay biến mất — nó chỉ *chuyển từ chỗ này sang chỗ khác*.

### Ví dụ đời thường

Bạn rút 5 triệu từ ATM:

| Tài khoản | Thay đổi |
|------------|----------|
| Tiền mặt (Tài sản) | +5,000,000 |
| Tài khoản ngân hàng (Tài sản) | -5,000,000 |
| **Tổng** | **0** |

### Quy tắc vàng

> **Mọi bút toán phải cân bằng = 0. Không bao giờ ngoại lệ.**

Nếu tổng không bằng 0 → có sai sót → phải tìm và sửa.

### Tại sao cần cho crypto?

- Không có ngân hàng giữ sổ sách cho bạn
- Mỗi giao dịch on-chain cần được ghi nhận đúng chuẩn kế toán
- Cơ quan thuế yêu cầu sổ sách rõ ràng, kiểm tra được

---

## 2. Bốn loại tài khoản

Mọi tài khoản kế toán đều thuộc 1 trong 4 loại:

| Loại | Tiếng Anh | Ý nghĩa | Ví dụ crypto |
|------|-----------|----------|--------------|
| **Tài sản** | Asset | Thứ bạn **SỞ HỮU** | ETH trong ví, USDC, tiền gửi Aave |
| **Nợ phải trả** | Liability | Thứ bạn **NỢ** | Vay từ Aave, nợ protocol |
| **Thu nhập** | Income | Tiền bạn **KIẾM ĐƯỢC** | Lãi staking, yield farming |
| **Chi phí** | Expense | Tiền bạn **CHI RA** | Gas fee, phí swap |

### Cách nhớ đơn giản

```
TÀI SẢN (Asset)     = Cái bạn có trong tay
NỢ (Liability)       = Cái bạn phải trả người khác
THU NHẬP (Income)    = Lý do bạn có thêm tiền
CHI PHÍ (Expense)    = Lý do bạn mất tiền
```

### Công thức kế toán cơ bản

```
Tài sản = Nợ phải trả + Vốn chủ sở hữu
```

Trong crypto cá nhân, "Vốn chủ sở hữu" ≈ tổng (Thu nhập - Chi phí) qua thời gian.

---

## 3. Bút toán (Journal Entry) và Splits

### Bút toán là gì?

Mỗi khi xảy ra giao dịch, ta tạo 1 **bút toán** gồm nhiều **dòng (splits)**:

```
Bút toán #001: Swap ETH → USDC
├── Dòng 1: Tài khoản ETH     → -1.0 ETH    (giảm ETH)
├── Dòng 2: Tài khoản USDC    → +2,500 USDC  (tăng USDC)
└── Tổng: 0 ✓ (cân bằng)
```

### Mỗi dòng (split) gồm gì?

| Trường | Ý nghĩa | Ví dụ |
|--------|----------|-------|
| Tài khoản | Tài khoản bị ảnh hưởng | "ETH:Wallet1" |
| Số lượng | Bao nhiêu token | -1.0 |
| Symbol | Token gì | ETH |
| Giá trị USD | Quy đổi ra USD tại thời điểm GD | $2,500 |
| Giá trị VND | Quy đổi ra VND | 62,500,000đ |

### Tại sao cần cả USD lẫn VND?

- USD: tiêu chuẩn quốc tế, giá crypto đều tính bằng USD
- VND: luật Việt Nam yêu cầu, thuế tính bằng VND

---

## 4. Ví dụ thực tế DeFi → Bút toán

### 4.1 Swap: Đổi 1 ETH lấy 2,500 USDC (trên Uniswap)

```
Loại: SWAP
┌─────────────────────┬──────────┬────────────┬─────────────────┐
│ Tài khoản           │ Số lượng │ Giá trị $  │ Giá trị VND     │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ ETH (Tài sản)       │ -1.0     │ -$2,500    │ -62,500,000đ    │
│ USDC (Tài sản)      │ +2,500   │ +$2,500    │ +62,500,000đ    │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ TỔNG                │          │ $0         │ 0đ              │
└─────────────────────┴──────────┴────────────┴─────────────────┘
```

**Giải thích:** Bạn bớt 1 ETH, nhận 2,500 USDC. Tổng giá trị không đổi.

### 4.2 Gửi tiền vào Aave: 1,000 USDC

```
Loại: DEPOSIT
┌──────────────────────────────┬──────────┬────────────┬─────────────────┐
│ Tài khoản                    │ Số lượng │ Giá trị $  │ Giá trị VND     │
├──────────────────────────────┼──────────┼────────────┼─────────────────┤
│ USDC (Tài sản - ví)         │ -1,000   │ -$1,000    │ -25,000,000đ    │
│ aUSDC (Tài sản - protocol)  │ +1,000   │ +$1,000    │ +25,000,000đ    │
├──────────────────────────────┼──────────┼────────────┼─────────────────┤
│ TỔNG                        │          │ $0         │ 0đ              │
└──────────────────────────────┴──────────┴────────────┴─────────────────┘
```

**Giải thích:** USDC rời ví → vào Aave. Vẫn là tài sản của bạn, chỉ đổi "chỗ để".

### 4.3 Vay từ Aave: 500 DAI

```
Loại: BORROW
┌──────────────────────────────┬──────────┬────────────┬─────────────────┐
│ Tài khoản                    │ Số lượng │ Giá trị $  │ Giá trị VND     │
├──────────────────────────────┼──────────┼────────────┼─────────────────┤
│ DAI (Tài sản - ví)          │ +500     │ +$500      │ +12,500,000đ    │
│ Nợ Aave DAI (Nợ phải trả)  │ -500     │ -$500      │ -12,500,000đ    │
├──────────────────────────────┼──────────┼────────────┼─────────────────┤
│ TỔNG                        │          │ $0         │ 0đ              │
└──────────────────────────────┴──────────┴────────────┴─────────────────┘
```

**Giải thích:** Bạn nhận DAI (tài sản tăng), nhưng đồng thời nợ Aave (nợ tăng). Net = 0.

### 4.4 Gas fee: 0.01 ETH

```
Loại: GAS_FEE
┌─────────────────────┬──────────┬────────────┬─────────────────┐
│ Tài khoản           │ Số lượng │ Giá trị $  │ Giá trị VND     │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ ETH (Tài sản)       │ -0.01    │ -$25       │ -625,000đ       │
│ Gas Fee (Chi phí)   │ +0.01    │ +$25       │ +625,000đ       │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ TỔNG                │          │ $0         │ 0đ              │
└─────────────────────┴──────────┴────────────┴─────────────────┘
```

**Giải thích:** ETH giảm vì trả gas. Gas được ghi vào chi phí.

### 4.5 Nhận lãi staking: 10 USDC

```
Loại: YIELD
┌─────────────────────┬──────────┬────────────┬─────────────────┐
│ Tài khoản           │ Số lượng │ Giá trị $  │ Giá trị VND     │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ USDC (Tài sản)      │ +10      │ +$10       │ +250,000đ       │
│ Lãi Aave (Thu nhập) │ -10      │ -$10       │ -250,000đ       │
├─────────────────────┼──────────┼────────────┼─────────────────┤
│ TỔNG                │          │ $0         │ 0đ              │
└─────────────────────┴──────────┴────────────┴─────────────────┘
```

**Giải thích:** USDC tăng (tài sản +). Nguồn gốc: thu nhập từ lãi (thu nhập là số âm trong kế toán kép — hơi ngược nhưng đúng convention).

---

## 5. FIFO là gì?

### Khái niệm

**FIFO = First In, First Out** — Mua trước, bán trước.

Khi bạn bán crypto, hệ thống tự khớp với lô mua **cũ nhất** trước.

### Ví dụ

```
Tháng 1: Mua 1 ETH giá $2,000  (Lô 1)
Tháng 3: Mua 1 ETH giá $3,000  (Lô 2)
Tháng 6: Bán 1 ETH giá $3,500

FIFO → khớp với Lô 1 (mua trước):
  Giá bán: $3,500
  Giá vốn: $2,000  (lô cũ nhất)
  Lãi:     $1,500

Còn lại: 1 ETH (Lô 2, giá vốn $3,000)
```

### Tại sao dùng FIFO?

- **Luật Việt Nam bắt buộc FIFO** (không được chọn LIFO hay Average)
- **GLOBAL_FIFO**: tất cả ví gộp chung 1 hàng đợi cho mỗi token
  - Mua ETH ở ví A, bán ETH ở ví B → vẫn khớp FIFO chung

### Thuật ngữ

| Tiếng Anh | Tiếng Việt | Ý nghĩa |
|------------|------------|----------|
| Open Lot | Lô mở | Lô mua chưa bán hết |
| Closed Lot | Lô đóng | Đã bán, tính được lãi/lỗ |
| Cost Basis | Giá vốn | Giá mua ban đầu |
| Realized Gain | Lãi thực hiện | Lãi/lỗ khi bán (giá bán - giá vốn) |
| Unrealized Gain | Lãi chưa thực hiện | Lãi/lỗ trên giấy (chưa bán) |

---

## 6. Thuế Việt Nam — Luật 71/2025

### Tóm tắt

| Hạng mục | Chi tiết |
|----------|----------|
| Luật | Luật Công nghệ số (No. 71/2025/QH15) |
| Thuế suất | **0.1%** trên giá trị mỗi lần chuyển nhượng |
| Miễn thuế | Giao dịch đơn lẻ > 20 triệu VND (~$800) được **MIỄN** |
| Phương pháp | FIFO bắt buộc |
| Đơn vị tiền | Khai bằng VND |
| Hạn nộp | Tự khai hàng năm, deadline **31/03** năm sau |

### Điểm đặc biệt (CỰC KỲ QUAN TRỌNG)

#### Thuế chuyển nhượng, KHÔNG PHẢI thuế lãi vốn

```
Ở nhiều nước: Thuế tính trên LÃI (gain) — bán lỗ thì không đóng thuế
Ở Việt Nam:   Thuế tính trên GIÁ TRỊ CHUYỂN NHƯỢNG — bán lỗ VẪN đóng thuế 0.1%
```

**Ví dụ:**
- Mua 1 ETH giá $3,000, bán giá $2,000 (lỗ $1,000)
- Giá trị chuyển nhượng = $2,000 × tỉ giá VND = 50,000,000 VND
- Thuế = 50,000,000 × 0.1% = **50,000 VND** (vẫn phải đóng dù lỗ!)

#### Ngưỡng miễn thuế

- Giao dịch > 20 triệu VND → **MIỄN** (nghe ngược đời nhưng đúng luật)
- Chỉ giao dịch nhỏ ≤ 20 triệu mới phải đóng

> **Câu hỏi cho kiểm toán viên:** Xác nhận lại logic miễn thuế — "giao dịch đơn lẻ > 20M VND được miễn" có đúng không? Hay là ngược lại?

#### Giao dịch nào bị tính thuế?

```
✅ Swap (đổi token)       → Tính thuế trên phần bán ra
✅ Bán crypto lấy fiat    → Tính thuế
✅ Bridge cross-chain      → Có thể bị tính (cần hỏi)
❓ Deposit vào protocol   → Cần xác nhận
❓ Withdraw từ protocol   → Cần xác nhận
❌ Gas fee                → Không phải chuyển nhượng
❌ Chuyển giữa ví mình   → Self-transfer, miễn
```

---

## 7. Sản phẩm LeafJots làm gì?

### Vấn đề

```
DeFi user ở Việt Nam:
  - Swap, stake, lend, borrow hàng trăm giao dịch/năm
  - Không ai giữ sổ sách
  - Luật 71/2025 yêu cầu tự khai thuế
  - Sàn ngoại (Uniswap, Aave) không thu thuế hộ
  → Cần tool tự động: đọc blockchain → tính thuế → xuất báo cáo
```

### Giải pháp

```
Bước 1: Kết nối ví     →  User nhập địa chỉ ví (ETH, Solana...)
Bước 2: Tải giao dịch  →  Hệ thống đọc từ blockchain tất cả TX
Bước 3: Phân tích TX   →  Parser tự nhận diện: swap, deposit, borrow...
Bước 4: Ghi sổ kế toán →  Tạo bút toán kép cho mỗi TX
Bước 5: Lấy giá        →  Tra giá USD + VND tại thời điểm giao dịch
Bước 6: Tính FIFO      →  Khớp lô mua-bán, tính lãi/lỗ
Bước 7: Tính thuế      →  Áp dụng 0.1% theo luật VN
Bước 8: Xuất báo cáo   →  File Excel 12+ sheet, nộp cho cơ quan thuế
```

### Dashboard cho user

- Xem tất cả ví, giao dịch, bút toán
- Debug khi parser nhận diện sai
- Xem lỗi, sửa thủ công nếu cần
- Tính thuế và tải báo cáo

### Báo cáo xuất ra (bangketoan.xlsx)

```
Sheet 1:  Tổng quan (Summary)
Sheet 2:  Bảng cân đối — theo số lượng
Sheet 3:  Bảng cân đối — theo giá trị USD
Sheet 4:  Bảng cân đối — theo giá trị VND
Sheet 5:  Báo cáo thu nhập - chi phí
Sheet 6:  Dòng tiền — theo số lượng
Sheet 7:  Dòng tiền — theo giá trị USD
Sheet 8:  Lãi/lỗ thực hiện (realized gains)
Sheet 9:  Lô mở (open lots — chưa bán)
Sheet 10: Sổ nhật ký (tất cả bút toán)
Sheet 11: Tổng hợp thuế
Sheet 12: Cảnh báo (warnings)
Sheet 13: Danh sách ví
Sheet 14: Cài đặt
```

---

## 8. Câu hỏi cần hỏi kiểm toán viên

### A. Về thuế crypto Việt Nam

1. **Thuế 0.1% — tính trên giá trị giao dịch hay giá trị lãi?**
   - Hiểu của mình: trên giá trị chuyển nhượng (kể cả khi lỗ)
   - Xác nhận đúng không?

2. **Ngưỡng miễn thuế 20 triệu VND — giao dịch > 20M được miễn hay < 20M được miễn?**
   - Luật viết "giao dịch đơn lẻ > 20M VND được miễn" — xin xác nhận logic

3. **Giao dịch nào tính là "chuyển nhượng"?**
   - Swap token A → token B: có
   - Deposit vào lending protocol (Aave): có hay không?
   - Withdraw từ lending: có hay không?
   - Bridge cross-chain (ETH mainnet → Arbitrum): có hay không?
   - Wrap/Unwrap (ETH → WETH): có hay không?

4. **Tỉ giá USD/VND dùng nguồn nào?**
   - Ngân hàng Nhà nước? Vietcombank? Trung bình?
   - Tại thời điểm giao dịch hay cuối ngày?

5. **Deadline khai thuế?**
   - 31/03 năm sau — xác nhận
   - Khai ở đâu? Mẫu biểu nào?

6. **Có hướng dẫn chính thức (circular/thông tư) chi tiết về thuế crypto chưa?**
   - Hay mới chỉ có luật khung?

### B. Về kế toán / sổ sách

7. **Double-entry cho crypto cá nhân — có chuẩn nào không?**
   - Hay tự thiết kế miễn nhất quán?

8. **Hệ thống tài khoản (Chart of Accounts) cho crypto?**
   - Mình dùng 4 loại: Asset, Liability, Income, Expense
   - Có cần thêm loại nào? (ví dụ Equity?)

9. **Phân loại DeFi positions:**
   - Deposit vào Aave → Tài sản hay chỉ đổi chỗ?
   - Vay từ Aave → Nợ phải trả, đúng không?
   - LP tokens (cung cấp thanh khoản) → phân loại thế nào?

10. **Gas fee → Chi phí hay trừ vào giá vốn?**
    - Ví dụ: gas $25 khi swap — ghi riêng thành chi phí? Hay cộng vào giá mua?

11. **Yield/Interest từ lending → Thu nhập thường hay thu nhập tài chính?**
    - Có phân biệt loại thu nhập không?

12. **Airdrop, farming rewards → ghi nhận thế nào?**
    - Thu nhập tại thời điểm nhận? Giá trị nào?

### C. Về báo cáo

13. **Báo cáo Excel mình xuất ra — có đủ cho cơ quan thuế không?**
    - Cần thêm gì? Bớt gì?

14. **Bảng cân đối cần ở thời điểm nào?**
    - Cuối năm (31/12)? Hay thời điểm tùy chọn?

15. **Có cần báo cáo theo quý không? Hay chỉ năm?**

### D. Về FIFO

16. **FIFO Global hay Per-wallet?**
    - Luật VN yêu cầu cụ thể?
    - Nếu có 5 ví, mua ETH ở ví A, bán ở ví B → FIFO chung?

17. **Cost basis có bao gồm gas fee không?**
    - Mua 1 ETH giá $2,000 + gas $25 → giá vốn = $2,000 hay $2,025?

18. **Transfer giữa ví mình (self-transfer) → có tính là chuyển nhượng không?**

### E. Về sản phẩm

19. **Nhu cầu thực tế của khách hàng:**
    - Ai sẽ dùng tool này? Cá nhân? Doanh nghiệp? Fund?
    - Họ cần gì nhất: tính thuế? Theo dõi portfolio? Cả hai?

20. **Kiểm toán viên có sẵn sàng review/validate output của tool không?**
    - Nếu có, cần format báo cáo thế nào để kiểm toán viên dễ kiểm tra?

---

## 9. Thuật ngữ kế toán ↔ tiếng Việt

| Tiếng Anh | Tiếng Việt | Giải thích nhanh |
|------------|------------|-------------------|
| Double-entry bookkeeping | Kế toán kép / Ghi sổ kép | Mỗi GD ghi 2 bên, tổng = 0 |
| Journal Entry | Bút toán | 1 bản ghi cho 1 giao dịch |
| Journal Split / Line | Dòng bút toán | 1 dòng trong bút toán |
| Debit | Nợ (bên Nợ) | Tăng tài sản / giảm nợ |
| Credit | Có (bên Có) | Giảm tài sản / tăng nợ |
| Asset | Tài sản | Cái bạn sở hữu |
| Liability | Nợ phải trả | Cái bạn nợ |
| Income / Revenue | Thu nhập / Doanh thu | Tiền kiếm được |
| Expense | Chi phí | Tiền chi ra |
| Equity | Vốn chủ sở hữu | Tài sản - Nợ |
| Chart of Accounts | Hệ thống tài khoản | Danh sách tất cả tài khoản |
| Balance Sheet | Bảng cân đối kế toán | Ảnh chụp tài chính tại 1 thời điểm |
| Income Statement | Báo cáo kết quả kinh doanh | Thu nhập vs chi phí trong 1 kỳ |
| Cost Basis | Giá vốn | Giá mua ban đầu |
| Realized Gain | Lãi thực hiện | Lãi khi đã bán |
| Unrealized Gain | Lãi chưa thực hiện | Lãi trên giấy |
| FIFO | Nhập trước xuất trước | Mua trước → bán trước |
| Reconciliation | Đối chiếu | So khớp sổ sách vs thực tế |
| Fiscal Year | Năm tài chính | Thường 01/01 - 31/12 |
| Tax Filing | Khai thuế | Nộp tờ khai cho cơ quan thuế |
| Audit | Kiểm toán | Kiểm tra sổ sách độc lập |
| Ledger | Sổ cái | Sổ tổng hợp tất cả tài khoản |
| Fair Market Value (FMV) | Giá trị hợp lý / Giá thị trường | Giá tại thời điểm GD |

### Thuật ngữ DeFi → Kế toán

| DeFi Action | Phân loại kế toán | Bút toán |
|-------------|-------------------|----------|
| Swap | Chuyển nhượng tài sản | Asset A giảm, Asset B tăng |
| Deposit (lending) | Chuyển đổi tài sản | Asset ví giảm, Asset protocol tăng |
| Borrow | Nhận tài sản + ghi nợ | Asset tăng, Liability tăng |
| Repay | Trả nợ | Asset giảm, Liability giảm |
| Yield | Thu nhập | Asset tăng, Income ghi nhận |
| Gas fee | Chi phí | Asset giảm, Expense ghi nhận |
| Liquidation | Thanh lý bắt buộc | Asset giảm, Liability giảm (+ có thể lỗ) |

---

## Tips cho buổi gặp

1. **Ghi chép lại** — đặc biệt các câu trả lời về thuế, sẽ ảnh hưởng trực tiếp code
2. **Hỏi ví dụ cụ thể** — "Nếu tôi swap 1 ETH lấy USDC trên Uniswap, thuế tính thế nào?"
3. **Xin tài liệu** — thông tư, mẫu biểu, hướng dẫn khai thuế
4. **Hỏi về edge cases** — DeFi có nhiều tình huống mà luật chưa cover rõ
5. **Show mockup** — nếu có thể, show Dashboard hoặc mẫu báo cáo Excel để kiểm toán viên feedback

---

*Tài liệu tạo bởi LeafJots team — 21/02/2026*
