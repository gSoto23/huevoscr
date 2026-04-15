import smtplib
from email.message import EmailMessage
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

def send_payment_receipt_email(order, to_email: str):
    """
    Sends a payment receipt strictly formatted to the provided email via SMTP.
    """
    if not to_email:
        logger.warning(f"No email provided for order {order.id}. Skipping email receipt.")
        return

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.error("SMTP credentials are not configured. Cannot send email.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"¡Recibo de Pago Exitoso! Orden #{order.id} - HuevosCR"
    msg['From'] = f"HuevosCR <{settings.SMTP_SENDER}>"
    msg['To'] = to_email

    # Format total
    total_fmt = f"₡{float(order.total_amount):,.2f}" if order.total_amount else "₡0.00"
    delivery_day = order.delivery_day or 'Por definir'
    customer_name = order.customer.name.split()[0] if order.customer and order.customer.name else "Cliente"

    # HTML Body Design
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
          <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #e67e22; font-size: 24px; margin: 0;">¡Pago Confirmado!</h1>
            <p style="color: #666666; font-size: 16px;">Gracias por preferir calidad y frescura.</p>
          </div>
          
          <p style="font-size: 16px; color: #333333;">Hola <b>{customer_name}</b>,</p>
          <p style="font-size: 16px; color: #333333;">Confirmamos que hemos recibido tu pago exitosamente. Aquí están los detalles de tu orden:</p>
          
          <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="border-bottom: 1px solid #eeeeee;">
              <td style="padding: 10px 0; color: #666666; font-weight: bold;">Número de Orden:</td>
              <td style="padding: 10px 0; color: #333333; text-align: right;">#{order.id}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
              <td style="padding: 10px 0; color: #666666; font-weight: bold;">Cantidad:</td>
              <td style="padding: 10px 0; color: #333333; text-align: right;">{order.quantity} cartón(es)</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
              <td style="padding: 10px 0; color: #666666; font-weight: bold;">Día de Entrega programado:</td>
              <td style="padding: 10px 0; color: #333333; text-align: right;">{delivery_day}</td>
            </tr>
            <tr style="border-bottom: 1px solid #eeeeee;">
              <td style="padding: 10px 0; color: #666666; font-weight: bold;">Método de Pago:</td>
              <td style="padding: 10px 0; color: #333333; text-align: right;">{order.payment_method or 'Electrónico'}</td>
            </tr>
            <tr style="background-color: #fff9f2; border-bottom: 2px solid #e67e22;">
              <td style="padding: 15px 10px; color: #e67e22; font-weight: bold; font-size: 18px;">Total Pagado:</td>
              <td style="padding: 15px 10px; color: #e67e22; font-weight: bold; font-size: 18px; text-align: right;">{total_fmt}</td>
            </tr>
          </table>
          
          <p style="text-align: center; font-size: 14px; color: #999999; margin-top: 30px;">
            Este es un recibo automático. Si tienes alguna consulta, puedes escribirnos por WhatsApp.
          </p>
          <div style="text-align: center; margin-top: 20px;">
             <a href="https://www.huevoscr.com" style="color: #e67e22; text-decoration: none; font-weight: bold;">www.huevoscr.com</a>
          </div>
        </div>
      </body>
    </html>
    """

    msg.set_content("Tu cliente de correo electrónico no soporta HTML.")
    msg.add_alternative(html_content, subtype='html')

    try:
        logger.info(f"Connecting to SMTP server {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email receipt successfully sent to {to_email} for order {order.id}")
    except Exception as e:
        logger.error(f"Failed to send email receipt for order {order.id} to {to_email}: {e}")
