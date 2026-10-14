from django.core.mail import send_mail


def notify_customer(order, subject, body):
    if not order.user.email:
        return
    try:
        send_mail(subject, body, None, [order.user.email], fail_silently=True)
    except Exception:
        pass


def order_placed(order):
    notify_customer(order, f"Lala Sarees order {order.number} received",
                    f"Hello {order.user.display_name},\n\nThank you for your order {order.number} of ₹{order.total}.\n"
                    f"We will keep you updated.\n\nLala Sarees, P Road, Kanpur\n9211420021 | 9638527410")


def order_shipped(order):
    notify_customer(order, f"Your order {order.number} has shipped",
                    f"Hello {order.user.display_name},\n\nYour order {order.number} is on its way.\n"
                    f"Courier: {order.courier or '-'}\nTracking ID: {order.tracking_id or '-'}\n\nLala Sarees")
