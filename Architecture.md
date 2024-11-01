# Architecture

## Architecture Diagram
![Architecture Diagram](./assets/architecture.png)

## ER Diagram
![ER Diagram](./assets/er_diagram.png)

## Technologies
- Django
- Django Rest Framework
- Stripe
- PostgreSQL    

## Flow
1. When a user creates a payment link, it is stored in the **PaymentLink** model.
2. Whenever the user clicks the payment link, they are taken to the **Custom Payment Page**.
3. The **Custom Payment Page** is built using Stripe Elements, which is a secure and customizable payment form hosted on the backend Django server.
4. The payment intent is created on the server side, and the client secret is sent to the custom payment page.
5. When customer makes the payment, it is processed, and the user is redirected to the success or failure page according to the payment status, which is hosted on the backend Django server.
6. The payment details are stored in the **Payment** model.
7. The backend server exposes a webhook that receives payment success/failure events from Stripe and updates the **Payment** model.
8. The **Analytics API** is responsible for tracking the payment status and other metrics.

## Usage of AI Tools
I used **Cursor AI** with **Claude 3.5 Sonnet** to write the code for the project. I also used **Claude Sonnet** to discuss the architecture with the AI and get feedback on the design.

### Example Prompts:
1. "How to create a payment link in Django?"
2. "How to create a custom payment page using Stripe Elements?"
3. "How to create a webhook in Django to receive payment success/failure events from Stripe?"
4. "How to track the payment status and other metrics using an analytics API?"
5. "Generate HTML page for success and failure."
6. "Write unit tests for the payment views".
7. "Integrate Google Analytics in payment page".

## Scalability:
- The system is designed to be scalable. The **Analytics API** can be scaled horizontally by adding more instances of the API.
- The Payment Model has columns for that support for disputes.
- We can add more columns to the Payment model to support more metrics.
- The Payment Page is hosted on the backend Django server, so it can be scaled horizontally by adding more instances of the Django server.
- The payment link and payment is associated with a user, so we can scale horizontally by adding more users.


