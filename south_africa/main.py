# NOTE: Public demo version. Does not submit reschedule/confirm when DRY_RUN=True.
# Use responsibly and comply with the website’s terms and all applicable laws.

import os
import time
import random
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
from plyer import notification
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO")
NOTIFY_EMAIL_PASSWORD = os.getenv("NOTIFY_EMAIL_PASSWORD")
SMS_NOTIFY_TO = os.getenv("SMS_NOTIFY_TO")  # SMS email addresses

DATE_RANGE_START_DT = datetime.today() + timedelta(days=4)
DATE_RANGE_END_DT = datetime.strptime("2025-08-15", "%Y-%m-%d")
CITIES = ["Cape Town", "Durban", "Johannesburg"]

# DRY_RUN=True will NOT submit reschedule/confirm actions (safe for demos)
DRY_RUN = True

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def notify(title, message):
    notification.notify(
        title=title,
        message=message,
        app_name="Visa Bot"
    )
    log(f"[NOTIFY] Desktop: {title} - {message}")

def send_email(subject, body):
    if not all([NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_PASSWORD]):
        return
    email_recipients = [email.strip() for email in NOTIFY_EMAIL_TO.split(",")] if NOTIFY_EMAIL_TO else []
    sms_recipients = [sms.strip() for sms in SMS_NOTIFY_TO.split(",")] if SMS_NOTIFY_TO else []
    recipients = email_recipients + sms_recipients

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = NOTIFY_EMAIL_FROM
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_PASSWORD)
            server.sendmail(NOTIFY_EMAIL_FROM, recipients, msg.as_string())
        log(f"[NOTIFY] Email/SMS sent: {subject}")
    except Exception as e:
        log(f"[ERROR] Email failed: {e}")

def polite_pause():
    delay = random.uniform(1.2, 3.7)
    time.sleep(delay)
    log(f"[PAUSE] Human-like pause for {delay:.2f}s")


        log(f"[WARNING] Failed to simulate mouse movement: {e}")

def login(driver):
    log("[STEP] Logging in...")
    driver.get("https://ais.usvisa-info.com/en-za/niv/users/sign_in")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "user_email")))
    driver.find_element(By.ID, "user_email").send_keys(EMAIL)
    polite_pause()
    driver.find_element(By.ID, "user_password").send_keys(PASSWORD)
    try:
        checkbox = driver.find_element(By.ID, "policy_confirmed")
        if not checkbox.is_selected():
            driver.execute_script("arguments[0].click();", checkbox)
    except:
        pass
    driver.find_element(By.NAME, "commit").click()
    log("[INFO] Login submitted.")

def continue_existing_appointment(driver):
    log("[STEP] Clicking 'Continue' on existing appointment page...")
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Continue"))
        ).click()
        return True
    except:
        return False

def click_reschedule(driver):
    log("[STEP] Clicking reschedule appointment link...")
    try:
        accordion = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reschedule appointment')]"))
        )        accordion.click()
        polite_pause()

        link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/appointment') and contains(text(), 'Reschedule Appointment')]"))
        )        link.click()
        return True
    except Exception as e:
        log(f"[ERROR] Reschedule click failed: {e}")
        return False

def select_city(driver, city):
    log(f"[STEP] Selecting city: {city}")
    try:
        dropdown = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_facility_id"))
        )
        Select(dropdown).select_by_visible_text(city)
        return True
    except Exception as e:
        log(f"[ERROR] City select failed: {e}")
        return False

def select_date_from_calendar(driver, target_date):
    log(f"[STEP] Selecting date {target_date.strftime('%Y-%m-%d')} from calendar...")
    date_input = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "appointments_consulate_appointment_date"))
    )
    date_input.click()

    while True:
        try:
            month_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-datepicker-group-first .ui-datepicker-month"))
            )
            year_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-datepicker-group-first .ui-datepicker-year"))
            )
            displayed_month = month_elem.text.strip()
            displayed_year = year_elem.text.strip()

            if not displayed_month or not displayed_year:
                log("[WARNING] Calendar header text empty, retrying...")
                time.sleep(1)
                continue

            displayed_date = datetime.strptime(f"{displayed_month} {displayed_year}", "%B %Y")

            if displayed_date.year > target_date.year or (displayed_date.year == target_date.year and displayed_date.month > target_date.month):
                driver.find_element(By.CSS_SELECTOR, ".ui-datepicker-prev").click()
            elif displayed_date.year < target_date.year or (displayed_date.year == target_date.year and displayed_date.month < target_date.month):
                driver.find_element(By.CSS_SELECTOR, ".ui-datepicker-next").click()
            else:
                all_days = driver.find_elements(By.CSS_SELECTOR, ".ui-datepicker-group-first td[data-handler='selectDay'] a")
                for day_elem in all_days:
                    if int(day_elem.text) == target_date.day:
                        day_elem.click()
                        return True
                log("[WARNING] Target day not found or is disabled.")
                return False
        except Exception as e:
            log(f"[ERROR] Calendar navigation failed: {e}")
            return False

def check_and_select_appointment(driver, city):
    log(f"[STEP] Checking for available appointment in {city}...")
    try:
        if not select_city(driver, city):
            return False

        date_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_date"))
        )
        tag_name = date_input.tag_name.lower()

        if tag_name == "input":
            current_date = max(DATE_RANGE_START_DT, datetime.today())
            last_date = DATE_RANGE_END_DT

            while current_date <= last_date:
                if select_date_from_calendar(driver, current_date):
                    notify("Visa Appointment Bot", f"Date found at {city}: {current_date.strftime('%Y-%m-%d')}")
                    send_email("Visa Date Found", f"Date: {current_date.strftime('%Y-%m-%d')} at {city}")

                    time_select = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_time"))
                    )
                    options = [opt.text for opt in time_select.find_elements(By.TAG_NAME, "option")]
                    log(f"[INFO] Available time slots: {options}")
                    Select(time_select).select_by_index(1)
                    log("[STEP] Selected first available time slot")
                    polite_pause()

                    reschedule_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and (@value='Reschedule' or contains(@value,'Reschedule'))]"))
                    )
                    if DRY_RUN:
                        log("[DRY_RUN] Would click Reschedule + Confirm here. Skipping irreversible actions.")
                        return True

                    reschedule_btn.click()
                    log("[STEP] Reschedule button clicked")
                    polite_pause()

                    try:
                        confirm_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes') or contains(text(), 'Continue') or contains(text(), 'Reschedule')]"))
                        )
                        log("[STEP] Clicking confirmation button...")
                        confirm_btn.click()
                        notify("Visa Appointment Bot", f"Appointment confirmed at {city}")
                        send_email("Visa Appointment Confirmed", f"Successfully confirmed appointment at {city} on {current_date.strftime('%Y-%m-%d')}")
                    except TimeoutException:
                        log("[WARNING] No confirmation popup appeared.")
                    return True
                else:
                    current_date += timedelta(days=1)
            return False
        else:
            log("[WARNING] Date input is not an input tag, calendar handling not implemented for this.")
            return False
    except Exception as e:
        log(f"[ERROR] Date check failed: {e}")
        return False

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        log("[INIT] Script started.")
        log(f"[CONFIG] Looking for appointments between {DATE_RANGE_START_DT.date()} and {DATE_RANGE_END_DT.date()}")
        login(driver)

        if not continue_existing_appointment(driver):
            log("[ERROR] No existing appointment to continue.")
            return

        if not click_reschedule(driver):
            log("[ERROR] Could not click reschedule.")
            return

        refresh_counter = 0

        while True:
            found = False
            for city in CITIES:
                if check_and_select_appointment(driver, city):
                    found = True
                    break

            if found:
                log("[SUCCESS] Appointment booked and confirmed. Exiting script.")
                return

            refresh_counter += 1
            wait_time = random.randint(180, 300)
            log(f"[WAIT] No appointment found. Refresh #{refresh_counter}. Sleeping {wait_time // 60}m {wait_time % 60}s")
            time.sleep(wait_time)
            driver.refresh()
            log("[STEP] Page refreshed.")

            if "sign_in" in driver.current_url or "Sign In" in driver.page_source:
                log("[WARNING] Detected sign out. Resetting session...")
                driver.quit()
                time.sleep(5)

                new_options = webdriver.ChromeOptions()
                new_options.add_argument("--start-maximized")
                driver = webdriver.Chrome(options=new_options)

                login(driver)

                if not continue_existing_appointment(driver):
                    log("[ERROR] No existing appointment after relogin.")
                    return

                if not click_reschedule(driver):
                    log("[ERROR] Could not click reschedule after relogin.")
                    return
    except Exception as e:
        log(f"[FATAL ERROR] {e}")
    finally:
        driver.quit()
        log("[EXIT] Browser closed.")

if __name__ == "__main__":
    main()
