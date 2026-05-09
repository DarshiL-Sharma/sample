from dotenv import load_dotenv
load_dotenv()
import uuid
import easyocr
import re
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from rapidfuzz import fuzz
from flask import  session
from dotenv import load_dotenv
load_dotenv()
import psycopg2
import os

def clean_amount(val):
    if not val:
        return None
    val = val.replace(",", "").strip()
    try:
        return float(val)
    except:
        return None

reader = easyocr.Reader(['en'])

print("data cleaning start ")
print("OCR activating ")

# function of OCR
def process_bill(image_path):
    result = reader.readtext(image_path)

    # Sort OCR results
    result = sorted(result, key=lambda x: (x[0][0][1], x[0][0][0]))
    lines = [item[1] for item in result]
    text = "\n".join(lines)

    # DATE
    date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', text)
    date = date_match.group() if date_match else None

    # TOTAL
    total_match = re.search(
        r'(grand\s*total|total\s*amount|amount\s*payable|net\s*total|total)\s*[:\-]?\s*₹?\s*(\d{1,7}(?:,\d{2,3})*(?:\.\d{2})?)',
        text,
        re.IGNORECASE
    )
    total = total_match.group(2) if total_match else None

    # SUBTOTAL
    subtotal_match = re.search(
        r'(sub\s*total|subtotal|item\s*total)\s*[:\-]?\s*₹?\s*(\d{1,7}(?:,\d{2,3})*(?:\.\d{2})?)',
        text,
        re.IGNORECASE
    )
    subtotal = subtotal_match.group(2) if subtotal_match else None

    # AMOUNT LOGIC (SAFE)
    if total:
        amount = total
    elif subtotal:
        amount = subtotal
    else:
        amount = None

    # VENDOR
    ignore_words = ["invoice", "total", "subtotal", "amount", "tax", "date", "receipt", "bill"]
    vendor = None
    for line in lines[:5]:
        if not any(word in line.lower() for word in ignore_words):
            if len(line.strip()) > 3:
                vendor = line.strip()
                break

    # INVOICE/
    invoice_match = re.search(
        r'(invoice\s*(?:no|#)?\s*[:\-]?\s*)([A-Za-z0-9\-\/]+)',
        text,
        re.IGNORECASE
    )
    invoice_no = invoice_match.group(2) if invoice_match else None
    return {
        "vendor": vendor,
        "amount": amount,
        "subtotal": subtotal,
        "total": total,
        "date": date,
        "invoice_no": invoice_no,
        "lines": lines
    }

print("OCR activated")
print("Rendering WEB INTERFACE ")
app = Flask(__name__)

db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
print("starting ")

db = SQLAlchemy(app)

class Bill(db.Model):
    __tablename__ = "Product_data"
    id = db.Column(db.Integer,primary_key = True)
    product_name = db.Column(db.String(200))
    vendor = db.Column(db.String(100))
    amount = db.Column(db.Float)
    subtotal = db.Column(db.Float)
    total = db.Column(db.Float)
    date = db.Column(db.String(20))
    invoice_no = db.Column(db.String(100))

with app.app_context():
    # db.drop_all()
    db.create_all()

def match_product_fuzzy(user_product, lines):
    best_line = None
    best_score = 0
    for line in lines:
        score = fuzz.token_set_ratio(user_product.lower(), line.lower())
        if score > best_score:
            best_score = score
            best_line = line
    return (best_line, best_score) if best_score > 70 else (None, best_score)


def get_market_price(product_name):
    db_url = os.environ.get("DATABASE_URL")

    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT product_name, price FROM products WHERE product_name ILIKE %s LIMIT 200",
        (f"%{product_name[:5]}%",)
    )

    rows = cursor.fetchall()
    conn.close()

    best_match = None
    best_score = 0
    best_price = None

    for db_name, price in rows:
        score = fuzz.token_set_ratio(product_name.lower(), db_name.lower())
        if score > best_score:
            best_score = score
            best_match = db_name
            best_price = price

    if best_score < 60:
        return None, None, best_score

    return best_match, best_price, best_score
def classify_price(bill_price, market_price):
    if bill_price is None or market_price is None:
        return "Unknown"

    diff = bill_price - market_price
    percent = (diff / market_price) * 100

    if abs(percent) <= 10:
        return "Fair"
    elif percent > 10:
        return "Overpriced"
    else:
        return "Underpriced"

print("rendering main page")
app.secret_key = os.environ.get("SECRET_KEY")
@app.route("/")
def main_page():
    return render_template("main_page.html")

from flask import request
import os

print("rendering upload")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['image']

    temp_path = f"temp_{uuid.uuid4().hex}.jpg"
    file.save(temp_path)  # temporary save

    try:
        data = process_bill(temp_path)
        session["ocr_lines"] = data["lines"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return render_template("review.html", data=data)

print("front page created ")
print("form is creating")

@app.route("/save",methods=["POST"])
def save():
    product_name = request.form.get("product_name")
    if not product_name or product_name.strip() == "":
        print("1")
        return render_template(
            "review.html",
            data={
                "vendor": request.form.get("vendor"),
                "amount": request.form.get("amount"),
                "subtotal": request.form.get("subtotal"),
                "total": request.form.get("total"),
                "date": request.form.get("date"),
                "invoice_no": request.form.get("invoice_no")
            },
            error="❌ No valid product name provided"
        )
    print("2")

    matched_line, score = match_product_fuzzy(product_name, session.get("ocr_lines", []))
    print("if fuzzy line so make it correct ")
    db_product, market_price, match_score = get_market_price(product_name)
    bill_price = clean_amount(request.form.get("amount"))

    print("product checking process")

    if market_price is None:
        verdict = "No Match Found"
    else:
        verdict = classify_price(bill_price, market_price)
    print("if product is found")
    new_bill = Bill(
        product_name = product_name,
        vendor = request.form.get("vendor"),
        amount = clean_amount(request.form.get("amount")),
        subtotal = clean_amount(request.form.get("subtotal")),
        total = clean_amount(request.form.get("total")),
        date = request.form.get("date"),
        invoice_no = request.form.get("invoice_no")
    )
    db.session.add(new_bill)
    db.session.commit()
    print("SAVE HIT")
    print(request.form)
    return render_template("result.html", data=new_bill,matched_line=matched_line,score = score,success=True,db_product=db_product,market_price=market_price,verdict=verdict)

if __name__ == "__main__":
    app.run(debug=True)