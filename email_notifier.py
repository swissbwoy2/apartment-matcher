import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from models import MatchResult
import os
from datetime import datetime

class EmailNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def send_matches_notification(self, email: str, matches: List[MatchResult]):
        """Send email notification with matching listings"""
        if not matches:
            return
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = f"New Matching Apartments Found - {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = self.smtp_username
        msg['To'] = email
        
        # Create HTML content
        html_content = self._create_html_content(matches)
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
        except Exception as e:
            print(f"Error sending email: {e}")

    def _create_html_content(self, matches: List[MatchResult]) -> str:
        """Create HTML email content from matches"""
        html = """
        <html>
            <head>
                <style>
                    .listing {
                        border: 1px solid #ddd;
                        margin: 10px 0;
                        padding: 15px;
                        border-radius: 5px;
                    }
                    .match-score {
                        color: #4CAF50;
                        font-weight: bold;
                    }
                    .price {
                        font-size: 1.2em;
                        color: #2196F3;
                    }
                    .features {
                        margin: 10px 0;
                    }
                    .feature {
                        background: #f0f0f0;
                        padding: 3px 8px;
                        border-radius: 3px;
                        margin-right: 5px;
                    }
                </style>
            </head>
            <body>
                <h2>New Matching Apartments Found</h2>
        """
        
        for match in matches:
            listing = match.listing
            html += f"""
                <div class="listing">
                    <h3>{listing.title}</h3>
                    <p class="match-score">Match Score: {match.match_score}%</p>
                    <p class="price">CHF {listing.price:,.2f}</p>
                    <p>{listing.location}</p>
                    <p>{listing.rooms} rooms | {listing.size}m²</p>
                    <div class="features">
                        {''.join(f'<span class="feature">{feature}</span>' for feature in listing.features)}
                    </div>
                    <p>Source: {listing.source}</p>
                    <p><a href="{listing.link}">View Details</a></p>
                </div>
            """
        
        html += """
            </body>
        </html>
        """
        return html