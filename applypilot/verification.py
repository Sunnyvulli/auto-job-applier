"""Conservative email-code extraction for an explicitly configured portal/sender."""
import re
from datetime import datetime,timezone,timedelta
from email import message_from_bytes
from email.policy import default
from email.utils import parseaddr,parsedate_to_datetime,getaddresses
from .mail import parse_message

PURPOSE=re.compile(r'verification code|one[ -]time (?:code|password)|security code|verify your (?:email|account)',re.I)

def extract_code(raw,address,sender,started_at,clock=None):
    msg=message_from_bytes(raw,policy=default)
    if parseaddr(str(msg.get('From','')))[1].lower()!=sender.lower():return None
    recipients=[a.lower() for _,a in getaddresses(msg.get_all('To',[])+msg.get_all('Delivered-To',[]))]
    if address.lower() not in recipients:return None
    try:date=parsedate_to_datetime(str(msg.get('Date','')))
    except (ValueError,TypeError,OverflowError):return None
    if not date.tzinfo:return None
    clock=clock or datetime.now(timezone.utc)
    start=datetime.fromisoformat(started_at)
    if not start.tzinfo:return None
    if date<max(start-timedelta(seconds=30),clock-timedelta(minutes=10)) or date>clock+timedelta(minutes=1):return None
    parsed=parse_message(raw);text=parsed['subject']+' '+parsed['body']
    if not PURPOSE.search(text):return None
    codes=set(re.findall(r'(?<!\d)\d{6}(?!\d)',text))
    return next(iter(codes)) if len(codes)==1 else None

def find_code(raw_messages,address,sender,started_at):
    codes={c for raw in raw_messages if (c:=extract_code(raw,address,sender,started_at))}
    if len(codes)!=1:raise ValueError('No unique recent verification code from the approved sender. Enter it manually.')
    return next(iter(codes))

def fill_code(page,code):
    # Only a single explicit OTP field, never an arbitrary password or text input.
    fields=page.locator('input[autocomplete="one-time-code"]:visible')
    if fields.count()==0:
        fields=page.get_by_label(re.compile(r'^(verification code|security code|one[ -]time (?:code|password))\s*[:*]?$',re.I)).filter(visible=True)
    if fields.count()!=1:raise ValueError('A single supported verification-code field was not found.')
    field=fields.first
    if field.get_attribute('type')=='password':raise ValueError('Password fields are not verification-code targets.')
    try:field.fill(code)
    except Exception:raise ValueError('Verification field could not be filled. Complete this step manually.') from None
