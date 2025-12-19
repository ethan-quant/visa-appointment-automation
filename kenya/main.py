import os
import time
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv
from plyer import notification

import smtplib
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


# ----------------------------
# Config (edit as needed)
# ----------------------------

COUNTRY_PATH = "en-ke"          # Kenya
VISA_TYPE_PATH = "niv"          # Non-immigrant visas
BASE_URL = "https://ais.usvisa-info.com/en-ke/niv"


# Kenya NIV is typically Nairobi; keep a list in case your account shows more facilities
CITIES = ["Nairobi"]

# Date window to search (adjust to your needs)
DATE_RANGE_START_DT = datetime.today() + timedelta(days=3)
DATE_RANGE_END_DT = datetime(2026, 1, 5)


# Refresh cadence (be respectful — don't hammer the site)
# DRY_RUN=True will NOT submit reschedule/confirm actions (safe for demos)
DRY_RUN = True

MIN_WAIT_SECONDS = 180
MAX_WAIT_SECONDS = 300


# ----------------------------
# Secrets / notifications
# ----------------------------

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

APPOINTMENT_URL = f"{BASE_URL}/schedule/{ACCOUNT_ID}/appointment"

NOTIFY_EMAIL_FROM = os.getenv("NOTIFY_EMAIL_FROM")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO")  # comma-separated
NOTIFY_EMAIL_PASSWORD = os.getenv("NOTIFY_EMAIL_PASSWORD")

SMS_NOTIFY_TO = os.getenv("SMS_NOTIFY_TO")      # comma-separated email-to-SMS gateways


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def notify(title: str, message: str) -> None:
    try:
        notification.notify(title=title, message=message, app_name="Visa Bot")
    except Exception:
        pass
    log(f"[NOTIFY] {title} - {message}")


def send_email(subject: str, body: str) -> None:
    # Sends one message to all email + SMS recipients (email-to-SMS gateways).
    if not all([NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_PASSWORD]):
        return

    email_recipients = [e.strip() for e in (NOTIFY_EMAIL_TO or "").split(",") if e.strip()]
    sms_recipients = [s.strip() for s in (SMS_NOTIFY_TO or "").split(",") if s.strip()]
    recipients = email_recipients + sms_recipients
    if not recipients:
        return

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


def build_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-sync")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    # If you need headless:
    # opts.add_argument("--headless=new")
    return webdriver.Chrome(options=opts)


def login(driver: webdriver.Chrome) -> None:
    log("[STEP] Logging in...")
    driver.get(f"{BASE_URL}/users/sign_in")

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "user_email")))
    driver.find_element(By.ID, "user_email").clear()
    driver.find_element(By.ID, "user_email").send_keys(EMAIL or "")

    driver.find_element(By.ID, "user_password").clear()
    driver.find_element(By.ID, "user_password").send_keys(PASSWORD or "")

    # Policy checkbox (sometimes present)
    try:
        checkbox = driver.find_element(By.ID, "policy_confirmed")
        if not checkbox.is_selected():
            driver.execute_script("arguments[0].click();", checkbox)
    except Exception:
        pass

    driver.find_element(By.NAME, "commit").click()
    log("[INFO] Login submitted.")


def continue_existing_appointment(driver: webdriver.Chrome) -> bool:
    log("[STEP] Clicking 'Continue' on existing appointment page (if present)...")
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Continue"))).click()
        return True
    except Exception:
        return False


def click_reschedule(driver: webdriver.Chrome) -> bool:
    log("[STEP] Navigating to reschedule page...")
    try:
        accordion = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reschedule appointment')]"
            ))
        )
        accordion.click()

        link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//a[contains(@href, '/appointment') and contains(., 'Reschedule Appointment')]"
            ))
        )
        link.click()
        return True
    except Exception as e:
        log(f"[ERROR] Reschedule navigation failed: {e}")
        return False
    
def accept_reschedule_warning(driver) -> bool:
    log("[STEP] Handling reschedule warning page (I understand + Continue)...")

    # If checkbox isn't present quickly, assume no warning gate
    try:
        cb = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "confirmed_limit_message"))
        )
    except Exception:
        log("[INFO] Warning checkbox not present; continuing.")
        return True

    # Wait until checkbox is interactable / rendered
    try:
        WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "confirmed_limit_message").is_displayed())
        WebDriverWait(driver, 15).until(lambda d: d.find_element(By.ID, "confirmed_limit_message").is_enabled())
    except Exception:
        pass

    # Click wrapper (icheck) if possible
    try:
        wrapper = driver.find_element(
            By.XPATH,
            "//div[contains(@class,'icheckbox')]//input[@id='confirmed_limit_message']/.."
        )
        driver.execute_script("arguments[0].click();", wrapper)
    except Exception:
        driver.execute_script("arguments[0].click();", cb)

    # Verify it checked
    time.sleep(0.3)
    cb = driver.find_element(By.ID, "confirmed_limit_message")
    if not cb.is_selected():
        log("[ERROR] Checkbox click did not stick.")
        return False
    log("[INFO] Checked 'I understand' checkbox.")

    # Click Continue
    cont = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @name='commit' and @value='Continue']"))
    )
    driver.execute_script("arguments[0].click();", cont)
    log("[INFO] Clicked Continue on warning page.")

    return True




def select_city(driver: webdriver.Chrome, city: str) -> bool:
    log(f"[STEP] Selecting facility/city: {city}")
    try:
        dropdown = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "appointments_consulate_appointment_facility_id"))
        )
        sel = Select(dropdown)

        # Try exact match first
        try:
            sel.select_by_visible_text(city)
            log(f"[INFO] Selected facility exactly: {city}")
        except Exception:
            # Fallback: partial match (in case option text is "Nairobi, Kenya", etc.)
            options = [o.text.strip() for o in sel.options if o.text.strip()]
            match = next((o for o in options if city.lower() in o.lower()), None)

            log(f"[DEBUG] Facility options: {options}")

            if not match:
                log(f"[ERROR] Could not find facility option containing '{city}'.")
                return False

            sel.select_by_visible_text(match)
            log(f"[INFO] Selected facility by partial match: {match}")

        # Give AIS time to populate the date field after facility selection
        time.sleep(1.5)
        return True

    except Exception as e:
        log(f"[ERROR] City select failed ({city}): {e}")
        return False



def select_date_from_calendar(driver: webdriver.Chrome, target_date: datetime) -> bool:
    """
    Select target_date from the AIS jQuery datepicker.

    Kenya often loads/enables the date input via AJAX after facility selection.
    So we:
    - wait for PRESENCE (not clickable)
    - wait until ENABLED
    - click via JS (more reliable)
    - navigate month/year and click the day if selectable
    - return False (not crash) if not available yet
    """
    try:
        # Wait for the date input to EXIST (Kenya can be slow)
        date_input = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//input[@id='appointments_consulate_appointment_date' "
                "or @name='appointments[consulate_appointment][date]' "
                "or contains(@id,'appointment_date')]"
            ))
        )

        # Wait for it to be enabled (sometimes disabled during AJAX)
        WebDriverWait(driver, 45).until(lambda d: date_input.is_enabled())

        # Open the datepicker (JS click is more reliable on AIS)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
        driver.execute_script("arguments[0].click();", date_input)

        while True:
            month_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-datepicker-group-first .ui-datepicker-month"))
            )
            year_elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-datepicker-group-first .ui-datepicker-year"))
            )

            displayed_month = month_elem.text.strip()
            displayed_year = year_elem.text.strip()
            displayed_date = datetime.strptime(f"{displayed_month} {displayed_year}", "%B %Y")

            if (displayed_date.year, displayed_date.month) > (target_date.year, target_date.month):
                prev_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-datepicker-prev"))
                )
                driver.execute_script("arguments[0].click();", prev_btn)

            elif (displayed_date.year, displayed_date.month) < (target_date.year, target_date.month):
                next_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-datepicker-next"))
                )
                driver.execute_script("arguments[0].click();", next_btn)

            else:
                # Only clickable days are in td[data-handler='selectDay']
                all_days = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".ui-datepicker-group-first td[data-handler='selectDay'] a"
                )
                for day_elem in all_days:
                    if int(day_elem.text) == target_date.day:
                        driver.execute_script("arguments[0].click();", day_elem)
                        return True

                # Day not selectable in this month view
                return False

    except Exception as e:
        # Important: don't kill the whole script; just treat as not ready / not available
        log(f"[INFO] Date field not ready or date not selectable for {target_date.strftime('%Y-%m-%d')}: {e}")
        return False



def check_and_select_appointment(driver: webdriver.Chrome, city: str) -> bool:
    log(f"[STEP] Checking appointment availability in {city}...")
    if not select_city(driver, city):
        return False

    # If there are no selectable days at all, we should refresh instead of looping dates
    try:
        date_input = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//input[@id='appointments_consulate_appointment_date' "
                "or @name='appointments[consulate_appointment][date]' "
                "or contains(@id,'appointment_date')]"
            ))
        )
        WebDriverWait(driver, 45).until(lambda d: date_input.is_enabled())
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", date_input)
        driver.execute_script("arguments[0].click();", date_input)

        # Look for ANY selectable day (if none exist, no appointments available right now)
        selectable_days = driver.find_elements(
            By.CSS_SELECTOR,
            ".ui-datepicker-group-first td[data-handler='selectDay'] a, td[data-handler='selectDay'] a"
        )

        if not selectable_days:
            log("[INFO] No selectable dates available right now. Will refresh and try again.")
            return False

    except Exception as e:
        log(f"[INFO] Datepicker not ready / no availability. Will refresh and try again. Details: {e}")
        return False

    # If we got here, at least one selectable day exists → now we do your normal day-by-day search window
    current_date = max(DATE_RANGE_START_DT, datetime.today())
    last_date = DATE_RANGE_END_DT

    while current_date <= last_date:
        if select_date_from_calendar(driver, current_date):
            notify("Visa Appointment Bot", f"Date found ({city}): {current_date.strftime('%Y-%m-%d')}")
            send_email("Visa Date Found", f"Date: {current_date.strftime('%Y-%m-%d')} | Facility: {city}")

            time_select = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_time"))
            )
            Select(time_select).select_by_index(1)

            reschedule_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//input[@type='submit' and (contains(@value,'Reschedule') or @value='Reschedule')]"
                ))
            )
            if DRY_RUN:
                log("[DRY_RUN] Would submit reschedule + confirm here. Skipping irreversible actions.")
                return True

            driver.execute_script("arguments[0].click();", reschedule_btn)
            log("[STEP] Reschedule submitted.")

            try:
                confirm_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(., 'Confirm') or contains(., 'Yes') or contains(., 'Continue')]"
                    ))
                )
                driver.execute_script("arguments[0].click();", confirm_btn)
                notify("Visa Appointment Bot", f"Appointment confirmed ({city})")
                send_email("Visa Appointment Confirmed", f"Confirmed: {city} on {current_date.strftime('%Y-%m-%d')}")
            except TimeoutException:
                log("[INFO] No confirmation popup appeared (may have confirmed immediately).")

            return True

        current_date += timedelta(days=1)

    log("[INFO] Selectable dates exist, but none within your target window. Will refresh and try again.")
    return False



def is_signed_out(driver: webdriver.Chrome) -> bool:
    try:
        return "sign_in" in driver.current_url or "Sign In" in driver.page_source
    except Exception:
        return True


def main() -> None:
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Missing EMAIL/PASSWORD in environment. Create a .env file from .env.example")

    driver = build_driver()
    try:
        log("[INIT] Kenya visa bot started.")
        log(f"[CONFIG] Window: {DATE_RANGE_START_DT.date()} -> {DATE_RANGE_END_DT.date()}")
        login(driver)

        if not continue_existing_appointment(driver):
            log("[ERROR] Could not find an existing appointment to continue. Make sure you're logged into the correct account.")
            return

        if not click_reschedule(driver):
            log("[ERROR] Could not reach the reschedule page.")
            return

        # ✅ ADD THIS BLOCK
        if not accept_reschedule_warning(driver):
            log("[ERROR] Failed to pass reschedule warning page.")
            return

        # ✅ Optional hard gate: ensure we’re past the warning and on the form page
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_facility_id"))
        )
        log("[INFO] Passed warning page. Facility dropdown is present.")

        refresh_counter = 0
        while True:
            for city in CITIES:
                if check_and_select_appointment(driver, city):
                    log("[SUCCESS] Appointment booked. Exiting.")
                    return
            ...


            refresh_counter += 1
            wait_time = random.randint(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS)
            log(f"[WAIT] None found. Refresh #{refresh_counter}. Sleeping {wait_time//60}m {wait_time%60}s")
            time.sleep(wait_time)

            try:
                driver.get(APPOINTMENT_URL)
                accept_reschedule_warning(driver)  # if the warning page appears again
                WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_facility_id"))
            )

            except WebDriverException:
                log("[WARNING] Refresh failed; rebuilding driver/session.")
                driver.quit()
                driver = build_driver()
                login(driver)

            if is_signed_out(driver):
                log("[WARNING] Signed out detected; re-logging in.")
                driver.quit()
                driver = build_driver()
                login(driver)

                if not continue_existing_appointment(driver):
                    log("[ERROR] No existing appointment after relogin.")
                    return

                if not click_reschedule(driver):
                    log("[ERROR] Could not reach reschedule after relogin.")
                    return

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        log("[EXIT] Browser closed.")


if __name__ == "__main__":
    main()
