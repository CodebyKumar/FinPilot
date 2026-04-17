"""
Sample SMS messages for testing the pocket-cfo-parser SMS parser.
60 realistic Indian bank UPI SMS texts across all major banks, merchants,
and transaction categories for comprehensive agent testing.
"""

SAMPLE_SMS = [
    # ── HDFC DEBITS ──────────────────────────────────────────────────────
    "UPDATE: Rs. 349.00 has been debited from your HDFC Bank A/c xx1234 on 17-Apr-26 to SWIGGY. UPI Ref No. 610543679802.",
    "Rs 2,199.00 debited from HDFC Bank A/c xx1234 on 17-Apr-26 to Amazon Seller Services. UPI Ref: 611022300991.",
    "Money Transfer: Rs 599.00 debited from A/c xx1234 on 16-04-2026 to VPA airtel@ybl. Ref: 610543229988.",
    "Rs. 8,500.00 debited from your HDFC Bank A/c xx1234 on 15-Apr-26 for EMI payment to HDFC Bank EMI. UPI Ref No. 609988771002.",
    "UPDATE: Rs. 1,450.00 has been debited from HDFC A/c xx1234 on 14-Apr-26 to Porter Logistics. UPI Ref: 610902889412.",
    "Rs 3,240.00 debited from HDFC Bank A/c xx1234 on 13-Apr-26 to AWS Cloud Services India. UPI Ref: 608812345123.",
    "UPDATE: Rs. 850.00 has been debited from HDFC A/c xx1234 on 12-Apr-26 to Rapido Ride. UPI Ref: 607933440021.",
    "Rs 12,000.00 debited from HDFC Bank A/c xx1234 on 11-Apr-26 to Rent Payment Property. UPI Ref: 607100029988.",
    "UPDATE: Rs. 499.00 has been debited from HDFC A/c xx1234 on 10-Apr-26 to Netflix Subscription. UPI Ref: 606544219900.",
    "Rs 1,875.00 debited from HDFC Bank A/c xx1234 on 09-Apr-26 to Myntra Fashion Store. UPI Ref: 605999112233.",
    "UPDATE: Rs. 2,500.00 has been debited from HDFC A/c xx1234 on 08-Apr-26 to Bluedart Courier. UPI Ref: 605200876543.",
    "Rs 750.00 debited from HDFC Bank A/c xx1234 on 07-Apr-26 to Apollo Pharmacy. UPI Ref: 604566221100.",
    "UPDATE: Rs. 1,100.00 has been debited from HDFC A/c xx1234 on 06-Apr-26 to Udemy Course. UPI Ref: 603899445566.",
    "Rs 5,000.00 debited from HDFC Bank A/c xx1234 on 05-Apr-26 to Delhivery Logistics Partner. UPI Ref: 603100998877.",

    # ── HDFC CREDITS ─────────────────────────────────────────────────────
    "Rs 15,000.00 deposited to your HDFC Bank A/c xx1234. Info: UPI-Razorpay Payments-610888331244. Avl Bal: Rs. 52,000.00.",
    "Rs 45,000.00 deposited to your HDFC Bank A/c xx1234. Info: Salary April 2026 Employer. Avl Bal: Rs. 67,000.00.",
    "Rs 8,200.00 deposited to your HDFC Bank A/c xx1234. Info: UPI-Rahul Sharma-611022300991. Avl Bal: Rs. 23,200.00.",

    # ── SBI DEBITS ───────────────────────────────────────────────────────
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs1250.50 on 17Apr26 trf to Raj Medical Store Ref No 610489000123.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 150.00 on 16Apr26 trf to Reliance Fresh Ref No 609211223344.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 3500.00 on 15Apr26 trf to Flipkart Online Ref No 608900112233.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 299.00 on 14Apr26 trf to Zepto Grocery Ref No 608100558899.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 4500.00 on 13Apr26 trf to Google Cloud Platform Ref No 607500889900.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 850.00 on 12Apr26 trf to Dunzo Delivery Ref No 606900223344.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 2800.00 on 11Apr26 trf to Hotel Booking OYO Ref No 606200556677.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 599.00 on 10Apr26 trf to Jio Prepaid Recharge Ref No 605500889900.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 18500.00 on 09Apr26 trf to Salary Payment Staff Ref No 604800112233.",
    "Dear SBI User, your A/c XXXXXX5678-debited by Rs 450.00 on 08Apr26 trf to BigBasket Groceries Ref No 604100445566.",

    # ── SBI CREDITS ──────────────────────────────────────────────────────
    "Dear Customer, A/c XXXXXX5678 is credited by Rs 1500.00 on 17-Apr-26. UPI Ref: 610512398450 (By: Neha Sharma). Bal: Rs 15,200.00",
    "Dear Customer, A/c XXXXXX5678 is credited by Rs 22000.00 on 10-Apr-26. UPI Ref: 605400987654 (By: Client Payment Anand Traders). Bal: Rs 38,200.00",
    "Dear Customer, A/c XXXXXX5678 is credited by Rs 5000.00 on 05-Apr-26. UPI Ref: 601900887766 (By: Cashfree Settlements). Bal: Rs 12,800.00",

    # ── ICICI DEBITS ─────────────────────────────────────────────────────
    "Dear Customer, Acct XX8901 is debited for Rs 850.00 on 17-04-2026 and credited to VPA zomato@icici. UPI Ref: 609812445566.",
    "Dear Customer, Acct XX8901 is debited for Rs 1,200.00 on 16-04-2026 and credited to VPA paytm@icici. UPI Ref: 609200334455.",
    "Dear Customer, Acct XX8901 is debited for Rs 5,499.00 on 15-04-2026 and credited to VPA amazon@icici. UPI Ref: 608700223366.",
    "Dear Customer, Acct XX8901 is debited for Rs 375.00 on 14-04-2026 and credited to VPA blinkit@icici. UPI Ref: 608200118899.",
    "Dear Customer, Acct XX8901 is debited for Rs 2,999.00 on 13-04-2026 and credited to VPA lenskart@icici. UPI Ref: 607600007788.",
    "Dear Customer, Acct XX8901 is debited for Rs 320.00 on 12-04-2026 and credited to VPA meesho@icici. UPI Ref: 607000996655.",
    "Dear Customer, Acct XX8901 is debited for Rs 6,800.00 on 11-04-2026 and credited to VPA digitalocean@icici. UPI Ref: 606400885544.",
    "Dear Customer, Acct XX8901 is debited for Rs 1,800.00 on 10-04-2026 and credited to VPA insurance@icici. UPI Ref: 605800774433.",

    # ── ICICI CREDITS ────────────────────────────────────────────────────
    "Your A/c no. XX8901 is credited with Rs. 12,000.00 on 13-04-2026 by UPI. UPI Ref. No. 608823129841. Info: Rent Payment.",
    "Your A/c no. XX8901 is credited with Rs. 30,000.00 on 01-04-2026 by UPI. UPI Ref. No. 600100009988. Info: Advance Client Kumar Industries.",

    # ── AXIS DEBITS ──────────────────────────────────────────────────────
    "INR 3,400.00 withdrawn from Axis A/c no. XX4555 on 17-04-26. Info: UPI/Amazon Pay/axisbank. Available Balance INR 42,100.00.",
    "INR 2,100.00 withdrawn from Axis A/c no. XX4555 on 16-04-26. Info: UPI/Flipkart/axisbank. Available Balance INR 39,900.00.",
    "INR 499.00 withdrawn from Axis A/c no. XX4555 on 15-04-26. Info: UPI/Swiggy/axisbank. Available Balance INR 38,400.00.",
    "INR 750.00 withdrawn from Axis A/c no. XX4555 on 14-04-26. Info: UPI/Pharmeasy/axisbank. Available Balance INR 37,650.00.",
    "INR 9,999.00 withdrawn from Axis A/c no. XX4555 on 13-04-26. Info: UPI/Microsoft Azure/axisbank. Available Balance INR 27,651.00.",
    "INR 22,000.00 withdrawn from Axis A/c no. XX4555 on 10-04-26. Info: UPI/Office Rent April/axisbank. Available Balance INR 14,000.00.",

    # ── AXIS CREDITS ─────────────────────────────────────────────────────
    "INR 50,000.00 credited to Axis A/c no. XX4555 on 01-04-26. Info: NEFT/Razorpay Settlements. Available Balance INR 64,000.00.",
    "INR 7,500.00 credited to Axis A/c no. XX4555 on 05-04-26. Info: UPI/Client Invoice Mehta Stores. Available Balance INR 71,500.00.",

    # ── KOTAK DEBITS ─────────────────────────────────────────────────────
    "You have sent Rs. 99.00 to Netflix via Kotak A/c XX3344. UPI Ref: 610511442288. Bal: Rs. 84,901.00.",
    "You have sent Rs. 650.00 to Dominos Pizza via Kotak A/c XX3344. UPI Ref: 609800556677. Bal: Rs. 84,251.00.",
    "You have sent Rs. 1,350.00 to Nykaa Fashion via Kotak A/c XX3344. UPI Ref: 609100223344. Bal: Rs. 82,901.00.",
    "You have sent Rs. 4,200.00 to Railway Ticket IRCTC via Kotak A/c XX3344. UPI Ref: 608300889900. Bal: Rs. 78,701.00.",
    "You have sent Rs. 2,500.00 to Ecom Express Courier via Kotak A/c XX3344. UPI Ref: 607500556677. Bal: Rs. 76,201.00.",
    "You have sent Rs. 15,000.00 to Processing Fee Bank Charges via Kotak A/c XX3344. UPI Ref: 606700223344. Bal: Rs. 61,201.00.",

    # ── KOTAK CREDITS ────────────────────────────────────────────────────
    "Rs. 25000 is credited to your Kotak Bank A/c XX3344 on 12-04-26 from UPI. Ref No: 610234771199. Bal: Rs. 85,000.",
    "Rs. 3500 is credited to your Kotak Bank A/c XX3344 on 08-04-26 from UPI. Ref: Phonepe Settlement. Bal: Rs. 62,000.",

    # ── SHOULD BE IGNORED (filters test) ─────────────────────────────────
    "DECLINED: Your UPI payment of Rs. 450.00 to Uber India via HDFC Bank A/c xx1234 failed. UPI Ref No. 610545672210.",
    "Your OTP to login to HDFC Bank MobileBanking is 845213. Do not share this with anyone.",
    "Exclusive Offer! Apply for SBI Credit Card today and get Amazon voucher Rs. 500. Click https://sbi.co.in. T&C Apply.",
]
