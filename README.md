# Dealflow Backend Assignment

This app serves as a backend for a payment link service.

## Features

### Standalone APIs

- **Create a Payment Link**: Generates a unique link for processing payments.
- **Analytics**: Tracks payment statuses and other key metrics for each payment link.

#### API Documentation

- Access the API documentation: [API Documentation](https://mysite-3e95.onrender.com/api/docs/)

### Payment Page

- Hosts a payment page corresponding to the payment link and handles the payment processing.

## Tech Stack

- **Python** 3.11
- **Django** 4.2.10
- **Django Rest Framework** 3.14.0
- **Stripe** 4.111.0
- **PostgreSQL**

## How to Run the App Locally

### Prerequisites

- Python 3.11
- PostgreSQL (ensure it's installed and running)
- Stripe Account (for obtaining API keys)

### Steps

1. **Create the Environment Configuration**:
   - Copy the `.env.example` file and rename it to `.env`.
   - Fill in the required environment variables, including your Stripe API keys.

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Collect Static Files**:
   ```bash
   python manage.py collectstatic
   ```

5. **Run the App**:
   ```bash
   python manage.py runserver
   ```  
6. The app will be available at `http://localhost:8000`.

