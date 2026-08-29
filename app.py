try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None
    MATPLOTLIB_AVAILABLE = False
import os
from openai import OpenAI
import csv
from flask import make_response
from flask import Flask, render_template, request, redirect, session, flash
import urllib.parse
import sqlite3
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'nexcore-leadflow-secret-key'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

mail = Mail(app)
app.secret_key = "nexcore_secret"
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
# CREATE DATABASE
def init_db():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        phone_number TEXT,
        business_type TEXT,
        status TEXT,
        followup_date TEXT
    )
''')

    conn.commit()
    conn.close()
    

init_db()
# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin123':

            session['user'] = username

            return redirect('/')

    return render_template('login.html')

# HOME PAGE
@app.route('/home')
def home():

    return render_template('home.html')
# DASHBOARD
@app.route('/')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    search = request.args.get('search', '')
    status = request.args.get('status', '')

    query = "SELECT * FROM leads WHERE 1=1"
    params = []

    if search:
        query += " AND customer_name LIKE ?"
        params.append(f"%{search}%")

    if status:
        query += " AND status=?"
        params.append(status)

    cursor.execute(query, params)
    leads = cursor.fetchall()

    conn.close()

    total_leads = len(leads)

    pending_count = len([lead for lead in leads if lead[4] == 'Pending'])
    contacted_count = len([lead for lead in leads if lead[4] == 'Contacted'])
    closed_count = len([lead for lead in leads if lead[4] == 'Closed'])

    potential_revenue = total_leads * 50000
    closed_revenue = closed_count * 50000

    conversion_rate = 0

    if total_leads > 0:
        conversion_rate = round((closed_count / total_leads) * 100, 1)

    hot_leads = pending_count

    from datetime import date

    today = date.today().strftime("%Y-%m-%d")

    today_followups = len([
        lead for lead in leads
        if lead[5] == today
    ])

    overdue_followups = len([
        lead for lead in leads
        if lead[5] < today and lead[4] != "Closed"
    ])

    # CREATE CHARTS

    labels = ['Pending', 'Contacted', 'Closed']
    values = [pending_count, contacted_count, closed_count]
    colors = ['orange', 'green', 'red']

    if MATPLOTLIB_AVAILABLE:

        plt.figure(figsize=(5,5))

        plt.pie(
            values,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90
        )

        plt.title("Lead Distribution Analytics")

        plt.savefig('static/chart.png')

        plt.close()

        plt.figure(figsize=(6,4))

        plt.bar(
            labels,
            values,
            color=colors,
            width=0.5
        )

        plt.title("Lead Status Analytics")

        plt.xlabel("Lead Status")

        plt.ylabel("Number of Leads")

        plt.grid(axis='y', linestyle='--', alpha=0.5)

        plt.savefig('static/bar_chart.png')

        plt.close()

    insights = []

    if pending_count > 0:
        insights.append(f"{pending_count} leads are still pending. Follow-up recommended.")

    if contacted_count > closed_count:
        insights.append("Contacted leads are increasing. Conversion opportunity is strong.")

    if closed_count > 0:
        insights.append(f"{closed_count} leads successfully closed.")

    recommendation = ""

    if pending_count > 0:
        recommendation = "You should follow up with pending leads today to improve conversion chances."

    elif closed_count > 0:
        recommendation = "Closed leads are improving. Your workflow performance looks strong."

    else:
        recommendation = "Lead activity is stable. Continue adding and tracking leads regularly."

    ai_message = ""

    if pending_count > 0:
        ai_message = "Follow up with pending leads today to improve conversion opportunities."

    elif contacted_count > 0:
        ai_message = "Contacted leads are active. Consider sending pricing or demo information."

    elif closed_count > 0:
        ai_message = "Closed leads indicate positive workflow efficiency."

    return render_template(
        'dashboard.html',
        leads=leads,
        total_leads=total_leads,
        pending_count=pending_count,
        contacted_count=contacted_count,
        closed_count=closed_count,
        insights=insights,
        recommendation=recommendation,
        today_followups=today_followups,
        overdue_followups=overdue_followups,
        ai_message=ai_message,
        potential_revenue=potential_revenue,
        closed_revenue=closed_revenue,
        conversion_rate=conversion_rate,
        today=today,
        hot_leads=hot_leads
    )
# LEADS PAGE

@app.route('/leads')
def leads_page():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads")
    leads = cursor.fetchall()

    conn.close()

    return render_template(
        'leads.html',
        leads=leads
    )


@app.route('/add-lead', methods=['GET', 'POST'])
def add_lead():

    if request.method == 'POST':

        customer_name = request.form['customer_name']
        phone_number = request.form['phone_number']
        business_type = request.form['business_type']
        status = request.form['status']
        followup_date = request.form['followup_date']
        email = request.form['email']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO leads (
            customer_name,
            phone_number,
            business_type,
            status,
            followup_date,
            email
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            customer_name,
            phone_number,
            business_type,
            status,
            followup_date,
            email
        ))

        conn.commit()
        conn.close()
        flash('Lead added successfully!', 'success')
        return redirect('/')

    return render_template('add_lead.html')
# ANALYTICS PAGE

@app.route('/analytics')
def analytics_page():

    return render_template('analytics.html')


# AI ASSISTANT

@app.route('/ai-assistant', methods=['GET', 'POST'])
def ai_assistant():

    response = ""

    if request.method == 'POST':

        question = request.form['question']

        question = question.lower()

        if "hot leads" in question:

            response = """
🔥 Hot Leads Analysis:

• Pending leads with High AI Score are priority customers.
• Contact them within 24 hours.
• Personalized WhatsApp follow-up recommended.
"""

        elif "follow up" in question:

            response = """
📞 Follow-Up Strategy:

• Focus on pending leads first.
• Send WhatsApp follow-up messages.
• Schedule another reminder within 2 days.
"""

        elif "sales" in question:

            response = """
📈 Sales Growth Suggestions:

• Target contacted leads aggressively.
• Offer personalized demos.
• Use AI-generated follow-ups for faster conversions.
"""

        elif "marketing" in question:

            response = """
🚀 Marketing Recommendations:

• Use WhatsApp campaigns.
• Run social media ads.
• Build automated AI customer engagement.
"""

        elif "conversion" in question:

            response = """
💡 Conversion Optimization:

• Fast response time improves lead conversion.
• Personalized communication increases trust.
• Closed leads can become referral sources.
"""

        else:

            response = """
🤖 NexCore AI suggests:

• Improve lead engagement.
• Prioritize high-score customers.
• Use AI follow-ups consistently.
"""

    return render_template(
        'ai_assistant.html',
        response=response
        
    )

# EDIT LEAD
@app.route('/edit-lead/<int:id>', methods=['GET', 'POST'])
def edit_lead(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        customer_name = request.form['customer_name']
        phone_number = request.form['phone_number']
        business_type = request.form['business_type']
        status = request.form['status']
        
        
        cursor.execute('''
            UPDATE leads
            SET customer_name=?,
                phone_number=?,
                business_type=?,
                status=?
            WHERE id=?
        ''', (customer_name,
              phone_number,
              business_type,
              status,
              id))

        conn.commit()
        conn.close()
        flash('Lead updated successfully!', 'success')
        return redirect('/')

    cursor.execute("SELECT * FROM leads WHERE id=?", (id,))
    lead = cursor.fetchone()

    conn.close()

    return render_template('edit_lead.html', lead=lead)
# EXPORT LEADS CSV
@app.route('/export-leads')
def export_leads():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads")

    leads = cursor.fetchall()

    conn.close()

    output = []

    output.append([
        'ID',
        'Customer Name',
        'Phone Number',
        'Business Type',
        'Status'
    ])

    for lead in leads:

        output.append([
            lead[0],
            lead[1],
            lead[2],
            lead[3],
            lead[4]
        ])

    response = make_response()

    response.headers["Content-Disposition"] = "attachment; filename=leads.csv"

    response.headers["Content-type"] = "text/csv"

    writer = csv.writer(response.stream)

    writer.writerows(output)

    return response
# LOGOUT
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')
# SMART AI FOLLOW-UP GENERATOR
@app.route('/generate-ai/<customer_name>/<business_type>/<status>')
def generate_ai(customer_name, business_type, status):

    customer_name = customer_name.title()
    business_type_clean = business_type.lower()
    status_clean = status.lower()

    if status_clean == "pending":

        ai_reply = f"""
Hello {customer_name},

Thank you for showing interest in NexCore LeadFlow CRM.

Since your enquiry is currently pending, we wanted to quickly follow up and understand your business requirements better.

For your {business_type} needs, NexCore can help you manage leads, track follow-ups, automate customer communication, and improve conversion efficiency.

Would you be available for a quick discussion today or tomorrow?

Regards,
NexCore Operations
"""

    elif status_clean == "contacted":

        ai_reply = f"""
Hello {customer_name},

Thank you for connecting with NexCore Operations.

Based on our discussion about your {business_type} requirement, NexCore LeadFlow CRM can help streamline your lead tracking, WhatsApp follow-ups, analytics, and customer engagement.

The next step would be to schedule a short demo and understand your workflow in detail.

Regards,
NexCore Operations
"""

    elif status_clean == "closed":

        ai_reply = f"""
Hello {customer_name},

Thank you for trusting NexCore Operations.

We’re glad to support your {business_type} growth journey with NexCore LeadFlow CRM.

We look forward to helping you manage leads better, improve follow-ups, and grow customer conversions.

Regards,
NexCore Operations
"""

    else:

        ai_reply = f"""
Hello {customer_name},

Thank you for your interest in NexCore LeadFlow CRM.

Our platform helps businesses automate lead management, follow-ups, analytics, and customer engagement.

We would be happy to understand your requirements and recommend the best solution for your business.

Regards,
NexCore Operations
"""

    return f"""
    <div style='
    font-family:Arial;
    padding:40px;
    background:#f1f5f9;
    min-height:100vh;
    '>

    <div style='
    background:white;
    padding:35px;
    border-radius:18px;
    box-shadow:0px 10px 30px rgba(0,0,0,0.15);
    max-width:850px;
    margin:auto;
    '>

    <h2 style='color:#0f172a;'>🤖 Smart AI Follow-Up Reply</h2>

    <p style='
    font-size:18px;
    line-height:1.8;
    white-space:pre-line;
    color:#1f2937;
    '>{ai_reply}</p>

    <br>

    <a href='/'
       style='
       background:#2563eb;
       color:white;
       padding:12px 22px;
       text-decoration:none;
       border-radius:10px;
       font-weight:bold;
       '>
       Back to Dashboard
    </a>

    </div>
    </div>
    """
@app.route('/whatsapp/<int:lead_id>')
def whatsapp(lead_id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    lead = cursor.fetchone()

    conn.close()

    customer_name = lead[1]
    status = lead[4]

    if status == "Pending":

        message = f"Hi {customer_name}, just following up regarding our earlier discussion. We'd love to help you move forward."

    elif status == "Contacted":

        message = f"Hi {customer_name}, thank you for connecting with NexCore. Sharing next steps for your business growth discussion."

    else:

        message = f"Hi {customer_name}, thank you for choosing NexCore. We appreciate your trust and look forward to supporting your growth."

    encoded_message = urllib.parse.quote(message)

    return redirect(
        f"https://web.whatsapp.com/send?phone=91{lead[2]}&text={encoded_message}"
    )

@app.route('/send-email/<int:lead_id>')
def send_email_to_lead(lead_id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    lead = cursor.fetchone()

    conn.close()

    if lead is None:
        return "Lead not found."

    if len(lead) < 7 or not lead[6]:
        return "No email address found for this lead."

    msg = Message(
        "NexCore Business Follow-Up",
        sender='nexcoreleadflow@gmail.com',
        recipients=[lead[6]]
    )

    msg.body = f"""
Hi {lead[1]},

Thank you for connecting with NexCore.

We’d love to help your business grow with smart CRM automation.

Regards,
NexCore Team
"""

    mail.send(msg)
    flash('Email sent successfully!', 'success')

    return redirect('/')
# DELETE LEAD
@app.route('/delete/<int:lead_id>')
def delete_lead(lead_id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM leads WHERE id=?", (lead_id,))

    conn.commit()
    conn.close()

    flash('Lead deleted successfully!', 'success')

    return redirect('/')
@app.route('/export-csv')
def export_csv():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads")
    leads = cursor.fetchall()

    conn.close()

    import csv
    from flask import Response

    def generate():
        data = []

        data.append([
            'ID',
            'Customer Name',
            'Phone',
            'Business Type',
            'Status',
            'Follow-Up Date',
            'Email'
        ])

        for lead in leads:
            data.append(lead)

        output = []

        for row in data:
            output.append(','.join(map(str, row)))

        return '\n'.join(output)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment;filename=nexcore_leads.csv"
        }
    )
@app.route('/googlefef3c30ff82f17c3.html')
def google_verification():
    return 'google-site-verification: googlefef3c30ff82f17c3.html'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)