# LeafJots -- Tổng Quan Sản Phẩm (Global)

> Tài liệu dành cho đội kinh doanh. Ngôn ngữ đơn giản, không yêu cầu nền tảng
> kỹ thuật blockchain hay kế toán chuyên sâu.

---

## 1. LeafJots Là Gì?

LeafJots là **phần mềm kế toán tự động cho tài sản số (crypto)**, chuyên xử lý
giao dịch DeFi (tài chính phi tập trung) và CEX (sàn tập trung).

Nói đơn giản: khi một người dùng crypto giao dịch trên blockchain hoặc trên sàn,
LeafJots sẽ:

1. **Đọc** tất cả giao dịch từ blockchain hoặc file CSV từ sàn
2. **Phân loại** từng giao dịch (swap, deposit, vay, trả nợ, nhận lãi...)
3. **Ghi sổ** theo chuẩn kế toán kép quốc tế (mỗi bút toán luôn cân bằng)
4. **Tính thuế** theo luật thuế của từng quốc gia (configurable)
5. **Xuất báo cáo** Excel chi tiết

---

## 2. Bài Toán LeafJots Giải Quyết

### Vấn đề chung toàn cầu

Hầu hết các quốc gia đang hoặc sẽ đánh thuế crypto. Người dùng DeFi gặp khó khăn
lớn nhất vì:

- **Không có trung gian** -- không ai ghi chép hay báo cáo hộ (khác sàn tập trung)
- **Giao dịch phức tạp** -- swap, yield farming, lending, staking, LP... không phải
  là mua/bán đơn giản
- **Đa chain, đa protocol** -- 1 người có thể dùng 5-10 protocols trên 3-4 blockchain
- **Khối lượng lớn** -- hàng ngàn giao dịch/năm, không thể ghi tay

### Ai cần LeafJots?

| Nhóm khách hàng | Nhu cầu |
|-----------------|---------|
| **Cá nhân đầu tư DeFi** | Khai thuế cuối năm, biết mình lãi/lỗ bao nhiêu |
| **Crypto fund / DAO treasury** | Báo cáo cho LP, audit, compliance |
| **Kế toán viên / Accounting firm** | Quản lý nhiều khách hàng crypto, xuất báo cáo chuẩn |
| **Người dùng sàn (Binance...)** | Import lịch sử giao dịch để tính thuế |

---

## 3. Sản Phẩm Làm Được Gì?

### 3.1 Đọc giao dịch từ blockchain (On-chain)

Thêm địa chỉ ví vào hệ thống, LeafJots tự động tải toàn bộ giao dịch.

**Blockchain hỗ trợ:** Ethereum, Solana (sắp tới: Arbitrum, Polygon, BSC).

### 3.2 Import từ sàn tập trung (CEX)

Upload file CSV xuất từ sàn. Hiện hỗ trợ **Binance** (48 loại giao dịch):

- Spot trade, Convert, P2P
- Deposit / Withdraw
- Earn (lãi linh hoạt, locked staking)
- Futures (PnL, phí, funding)
- Margin (vay, trả, thanh lý)
- Flexible Loan, token đặc biệt (WBETH, BFUSD...)

Kế hoạch: OKX, Bybit, và generic CSV template.

### 3.3 Phân loại tự động (Parser Engine) -- Lõi công nghệ

Hệ thống tự động nhận diện từng giao dịch thuộc loại nào:

| Loại giao dịch | Ý nghĩa |
|----------------|---------|
| **Swap** | Đổi token A lấy token B |
| **Deposit / Withdraw** | Gửi vào / Rút ra khỏi protocol |
| **Borrow / Repay** | Vay / Trả nợ (DeFi lending) |
| **Yield / Interest** | Nhận lãi, reward |
| **Staking** | Gửi token nhận lãi (Lido, Pendle...) |
| **Gas fee** | Phí giao dịch blockchain |
| **Transfer** | Chuyển token giữa ví |
| **Liquidity** | Cung cấp thanh khoản (LP) |

**Tỷ lệ phân loại thành công: ~95%** trên dữ liệu thực.

**DeFi protocols hỗ trợ:** Uniswap V3, Aave V3, Curve, PancakeSwap, Morpho Blue,
Lido (stETH/wstETH), Pendle.

**Chiến lược phân loại:**
```
Tầng 1: Generic Parser       -- tự detect chuyển token, gas           → 60% TX
Tầng 2: Generic Swap Parser  -- nhận diện pattern đổi token A↔B       → 80% TX
Tầng 3: Protocol-specific    -- Aave, Uniswap, Curve... (chính xác)  → 95% TX
Tầng 4: Manual review        -- 5% còn lại flag lên dashboard        → 100%
```

### 3.4 Kế toán kép (Double-entry Journal)

Mỗi giao dịch ghi thành bút toán kế toán kép, **luôn cân bằng**:

```
Ví dụ: Swap 1 ETH -> 2,500 USDC

  Tài khoản ETH     : -1 ETH    (-2,500 USD)
  Tài khoản USDC    : +2,500    (+2,500 USD)
  ───────────────────────────────────────────
  Tổng              :            0 USD  (cân bằng)
```

Nguyên tắc: **mọi bút toán phải tổng = 0**. Nếu không cân, hệ thống cảnh báo ngay.
Đây là tiêu chuẩn kế toán quốc tế, áp dụng cho mọi quốc gia.

### 3.5 Tính lãi/lỗ (Capital Gains -- FIFO)

- **FIFO** (First In First Out): khi bán token, giá vốn tính theo lô mua sớm nhất
- **Realized gains**: lãi/lỗ đã thực hiện (đã bán)
- **Open lots**: vị thế đang giữ (chưa bán), lãi/lỗ chưa thực hiện
- Hỗ trợ cả **Global FIFO** (gộp tất cả ví) và **Per-wallet FIFO**

### 3.6 Tax Engine (Cấu hình theo quốc gia)

Tax engine của LeafJots được thiết kế **configurable** -- luật thuế mỗi nước khác
nhau, chỉ cần cấu hình rule:

| Tham số | Ví dụ |
|---------|-------|
| Thuế suất chuyển nhượng | 0.1% (VN), capital gains rate (US, EU...) |
| Phương pháp tính giá vốn | FIFO (bắt buộc ở VN), LIFO, specific ID... |
| Ngưỡng miễn thuế | VND 20M (VN), £12,300 (UK), $0 (US)... |
| Đơn vị tiền báo cáo | VND, USD, EUR, GBP... |
| Holding period | Short/Long term (US: 1 năm), flat rate (VN)... |

**Hiện tại đã implement:** Vietnam (0.1% transfer tax, FIFO, VND 20M exemption).
Các jurisdiction khác sẽ mở rộng dần.

### 3.7 Xuất báo cáo (Report)

Excel report với 14+ sheet:

| Sheet | Nội dung |
|-------|----------|
| summary | Tổng quan: tài sản, thu nhập, thuế |
| balance_sheet_by_qty | Bảng cân đối theo số lượng token |
| balance_sheet_by_value | Bảng cân đối theo giá trị (USD, local currency) |
| income_statement | Thu nhập: lãi vay, reward, yield... |
| realized_gains | Chi tiết lãi/lỗ đã thực hiện |
| open_lots | Vị thế đang mở (lot nào mua khi nào, giá bao nhiêu) |
| tax_summary | Tổng thuế phải nộp |
| journal | Toàn bộ bút toán chi tiết |
| warnings | Cảnh báo: giao dịch lỗi, giá thiếu, bất cân bằng |

### 3.8 Quản lý đa khách hàng (Multi-Entity)

- Tạo nhiều entity (cá nhân, quỹ, công ty) trong cùng hệ thống
- Mỗi entity có ví, giao dịch, sổ kế toán, báo cáo **hoàn toàn riêng biệt**
- Chuyển đổi entity bằng dropdown, mọi trang tự lọc dữ liệu
- Phù hợp cho accounting firm quản lý portfolio khách hàng

### 3.9 Web Dashboard

11 trang web dashboard chạy trên trình duyệt:

| Trang | Chức năng |
|-------|-----------|
| Dashboard | Tổng quan: số ví, TX, parse rate, lỗi |
| Wallets | Thêm/xoá ví, sync dữ liệu |
| Transactions | Xem/lọc giao dịch, chi tiết TX |
| Parser Debug | Test parse 1 TX, xem parser nào chạy, kết quả |
| Journal | Xem bút toán kế toán kép + splits |
| Accounts | Cây tài khoản + số dư |
| Errors | Lỗi parse, TX unknown, giá thiếu |
| Tax | Tính thuế, xem gains, open lots |
| Reports | Tạo + tải báo cáo Excel |
| Import | Upload CSV Binance, xem tiến trình, lỗi |
| Entity Manager | Tạo/quản lý khách hàng |

---

## 4. Quy Trình Sử Dụng

```
Bước 1: Tạo Entity (khách hàng / quỹ)
         ↓
Bước 2: Thêm ví blockchain → Sync
        hoặc Upload CSV từ sàn
         ↓
Bước 3: Hệ thống tự phân loại + ghi sổ kế toán
         ↓
Bước 4: Review lỗi (nếu có) -- ~5% TX cần xem xét
         ↓
Bước 5: Chạy tính thuế → xem lãi/lỗ, thuế
         ↓
Bước 6: Xuất báo cáo Excel → nộp thuế
```

---

## 5. Lợi Thế Cạnh Tranh

| Đặc điểm | LeafJots | Koinly / CoinTracker / TokenTax |
|-----------|----------|--------------------------------|
| **DeFi accuracy** | 95% parse rate, 12 parsers chuyên biệt | Thường kém chính xác với DeFi phức tạp |
| **Kế toán kép** | Chuẩn double-entry, mọi entry cân bằng | Phần lớn chỉ track portfolio, không phải kế toán thật |
| **Multi-jurisdiction** | Configurable tax rules per country | Hỗ trợ nhiều nước nhưng rule cứng |
| **Dữ liệu** | Self-hosted, dữ liệu nằm tại chỗ | Cloud, dữ liệu trên server bên thứ 3 |
| **Multi-entity** | Quản lý nhiều khách hàng trong 1 hệ thống | Mỗi account = 1 entity, không quản lý tập trung |
| **Tuỳ chỉnh** | Open source, tuỳ chỉnh được | Closed source |
| **Giá** | Self-hosted (không subscription) | $49-299/năm/entity |

---

## 6. Tầm Nhìn Mở Rộng (Roadmap)

### Đã hoàn thành

| Version | Nội dung |
|---------|----------|
| v1.0 | Nền tảng: blockchain reader, parser, journal, FIFO, tax, report |
| v2.0 | Thêm protocol: Morpho Blue, Lido, Pendle + parser diagnostics |
| v3.0 | Multi-entity + Binance CSV import (48 operation types) |

### Sắp tới

| Hướng | Nội dung |
|-------|----------|
| **Multi-chain** | Arbitrum, Polygon, BSC, Base... |
| **Multi-CEX** | OKX, Bybit, generic CSV template |
| **Multi-jurisdiction** | US (capital gains), EU (MiCA), UK, Singapore, HK... |
| **Auth & permissions** | Multi-user, role-based access (Admin, Accountant, Viewer) |
| **Cloud deployment** | SaaS option ngoài self-hosted |
| **More protocols** | GMX, Compound, Maker, Balancer... |

---

## 7. Thuật Ngữ Cần Biết

| Thuật ngữ | Giải thích đơn giản |
|-----------|---------------------|
| **Blockchain** | "Sổ cái công khai" ghi lại mọi giao dịch, không ai sửa được |
| **DeFi** | Tài chính phi tập trung -- vay/cho vay/giao dịch trực tiếp trên blockchain |
| **CEX** | Sàn tập trung (Binance, OKX...) -- có công ty vận hành, giữ tiền hộ |
| **DEX** | Sàn phi tập trung (Uniswap...) -- giao dịch trực tiếp, không trung gian |
| **Wallet (Ví)** | Tài khoản trên blockchain, xác định bằng địa chỉ (vd: 0xABC...123) |
| **Token** | Đơn vị tài sản số (ETH, USDC, DAI, BTC...) |
| **Swap** | Đổi token A lấy token B |
| **Gas fee** | Phí giao dịch blockchain (giống phí chuyển khoản) |
| **Staking** | "Gửi tiết kiệm" token để nhận lãi |
| **Lending / Borrowing** | Cho vay / Đi vay trên DeFi |
| **Yield** | Lợi nhuận từ DeFi (lãi vay, reward, farming...) |
| **FIFO** | First In First Out -- bán thì tính giá vốn theo lô mua sớm nhất |
| **Capital Gains** | Lãi/lỗ khi bán tài sản (= giá bán - giá mua) |
| **Journal Entry** | Bút toán kế toán -- ghi nhận 1 giao dịch vào sổ sách |
| **Double-entry** | Kế toán kép -- mỗi giao dịch ghi 2 vế, luôn cân bằng |
| **Entity** | Đơn vị kế toán (cá nhân, quỹ, công ty) = 1 khách hàng |
| **Protocol** | Ứng dụng DeFi cụ thể (Uniswap, Aave, Curve...) |
| **EVM** | Ethereum Virtual Machine -- công nghệ chung cho Ethereum và các chain tương thích |

---

## 8. Kịch Bản Demo

### Demo DeFi (chính)

1. Mở dashboard -- giới thiệu tổng quan
2. Tạo entity demo
3. Thêm 1 ví Ethereum -- bấm Sync
4. Xem giao dịch tải về -- chỉ ra swap, deposit, borrow...
5. Parser Debug -- show hệ thống tự nhận diện loại TX
6. Journal -- show kế toán kép, mọi entry cân bằng
7. Tax Calculator -- show FIFO gains, thuế
8. Xuất Excel -- mở file, show các sheet

### Demo CEX (Binance)

1. Upload CSV Binance
2. Show phân loại 48 loại giao dịch
3. Show summary: thành công / lỗi
4. Xem journal entries sinh ra từ CSV

---

## 9. Thống Kê Kỹ Thuật (Tham Khảo)

| Metric | Giá trị |
|--------|---------|
| Test cases | 444 passing |
| Lint/TS errors | 0 |
| Active parsers | 12 |
| API endpoints | 43+ |
| Web pages | 11 |
| Binance op types | 48 covered |
| Parse success rate | ~95% on real data |

---

*Tài liệu cập nhật: 2026-02-20*
