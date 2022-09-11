from venmo_api import Client, PaymentPrivacy, PaymentStatus
import boto3
from botocore.exceptions import ClientError

'''
TODO:
    - Implement logging on requesting secret from secretsmanager, perhaps we could just set it as an env variable
    - Stop lambda CRON operation in cancel method
    - Write to DB successful transactions for users with latest transaction ID
'''

def get_secret():
    # Retrieve access_token from secrets manager, store errors in DB
    session = boto3.session.Session()
    client = session.Client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        elif e.response['Error']['Code'] == 'DecryptionFailure':
            print("The requested secret can't be decrypted using the provided KMS key:", e)
        elif e.response['Error']['Code'] == 'InternalServiceError':
            print("An error occurred on service side:", e)
    else:
        text_secret_data = get_secret_value_response['SecretString']

    return text_secret_data


class Venmo:

    def __init__(self, access_token):
        self.venmo = Client(access_token=access_token)
        self.active = True

    def request_money(self, user, amount, message, privacy=PaymentPrivacy.PUBLIC):
        # Request money
        my_boy = self.venmo.user.get_user_by_username(user)
        payment_request = self.venmo.payment.request_money(
            amount,
            message,
            my_boy.id,
            privacy)
        return payment_request

    def get_requested_payment(self, amount):
        # Find the requested payment ID
        requested_pending_payments = self.venmo.payment.get_charge_payments()
        for transaction in requested_pending_payments:
            if transaction.amount == amount:
                return transaction
        return None

    def remind_payment(self, payment_id):
        # if payment can be reminded, do so
        return self.venmo.payment.remind_payment(payment_id)

    def cancel_operation(self):
        # stop lambda CRON operation
        self.active = False
        '''
        cancel lambda CROM operation here.... 
        '''


if __name__ == "__main__":
    # Constants
    secret_name = "venmo_access_token"
    region_name = "us-east-1"
    user_name = "Luigi-Mangini"
    request_message = "This is an automated request. Pay to cancel."
    requested_amount = 0.69
    access_token = get_secret()
    # access_token = ""

    v = Venmo(access_token=access_token)
    v.request_money(user_name)
    payment = v.get_requested_payment(requested_amount)
    if payment is not None:
        if payment.status == PaymentStatus.SETTLED:
            v.cancel_operation()
        elif payment.status == PaymentStatus.PENDING:
            reminded = v.remind_payment()
        else:
            v.request_money(user_name, requested_amount, request_message)
    else:
        v.request_money(user_name, requested_amount, request_message)
