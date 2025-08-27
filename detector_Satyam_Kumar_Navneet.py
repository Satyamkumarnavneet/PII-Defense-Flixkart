import csv
import json
import re
import sys
from copy import deepcopy

# Check for standalone PII
def is_standalone_pii(key, value):
    value = str(value).strip()
    if key == 'phone':
        return bool(re.match(r'^\d{10}$', value))
    elif key == 'aadhar':
        cleaned = re.sub(r'\s+', '', value)
        return bool(re.match(r'^\d{12}$', cleaned))
    elif key == 'passport':
        return bool(re.match(r'^[A-Z]\d{7}$', value))
    elif key == 'upi_id':
        return '@' in value and len(value.split('@')) == 2 and value.split('@')[1]
    return False

# Mask strings
def mask_string(value):
    v_len = len(value)
    if v_len <= 3:
        return 'X' * v_len
    return value[0] + 'X' * (v_len - 2) + value[-1]

# Masking email local part
def mask_local_part(part):
    p_len = len(part)
    if p_len <= 3:
        return 'X' * p_len
    return part[:2] + 'XXX'

# Mask PII values
def mask_value(key, value):
    value = str(value).strip()
    if key == 'phone':
        if is_standalone_pii(key, value):
            return value[:2] + 'X' * 6 + value[-2:]
    elif key == 'aadhar':
        cleaned = re.sub(r'\s+', '', value)
        if is_standalone_pii(key, value):
            return cleaned[:4] + 'X' * 4 + cleaned[-4:]
    elif key == 'passport':
        if is_standalone_pii(key, value):
            return value[0] + 'X' * 6 + value[-1]
    elif key == 'upi_id':
        if is_standalone_pii(key, value):
            parts = value.split('@', 1)
            user = parts[0]
            domain = '@' + parts[1]
            if re.match(r'^\d{10}$', user):
                masked_user = mask_value('phone', user)
            else:
                masked_user = mask_string(user)
            return masked_user + domain
    elif key == 'name':
        words = re.split(r'\s+', value)
        masked_words = [mask_string(word) for word in words]
        return ' '.join(masked_words)
    elif key in ['first_name', 'last_name', 'device_id']:
        return mask_string(value)
    elif key == 'email':
        if '@' in value:
            local, domain = value.split('@', 1)
            local_parts = local.split('.')
            masked_local_parts = [mask_local_part(p) for p in local_parts]
            masked_local = '.'.join(masked_local_parts)
            return masked_local + '@' + domain
    elif key == 'address':
        return '[REDACTED_ADDRESS]'
    elif key == 'ip_address':
        if re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', value):
            parts = value.split('.')
            return '.'.join(parts[:3]) + '.XXX'
        return value
    return value

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python detector_Satyam_Kumar_Navneet.py <input_csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "redacted_output_Satyam_Kumar_Navneet.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as out_f:
        writer = csv.writer(out_f)
        writer.writerow(['record_id', 'redacted_data_json', 'is_pii'])

        with open(input_file, 'r', encoding='utf-8') as in_f:
            reader = csv.reader(in_f)
            next(reader, None)
            for row in reader:
                if len(row) != 2:
                    continue
                record_id = row[0]
                json_str = row[1]
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue

                redacted_data = deepcopy(data)
                is_pii_flag = False
                # Check and redact standalone PII
                standalone_keys = ['phone', 'aadhar', 'passport', 'upi_id']
                for sk in standalone_keys:
                    if sk in data:
                        s_val = str(data[sk])
                        if is_standalone_pii(sk, s_val):
                            is_pii_flag = True
                            redacted_data[sk] = mask_value(sk, s_val)
                # Check for combinatorial PII
                has_full_name = False
                name_keys_to_redact = []
                if 'name' in data:
                    name_val = str(data['name']).strip()
                    words = re.split(r'\s+', name_val)
                    if len(words) >= 2:
                        has_full_name = True
                        name_keys_to_redact.append('name')
                if 'first_name' in data and 'last_name' in data:
                    last_name_val = str(data['last_name']).strip()
                    if len(last_name_val) > 1:
                        has_full_name = True
                        if 'first_name' not in name_keys_to_redact:
                            name_keys_to_redact.append('first_name')
                        if 'last_name' not in name_keys_to_redact:
                            name_keys_to_redact.append('last_name')

                email_val = str(data.get('email', '')).strip()
                has_email = 'email' in data and bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_val))

                address_val = str(data.get('address', '')).strip()
                has_address = 'address' in data
                if has_address:
                    has_pin = bool(re.search(r'\b\d{5,6}\b', address_val))
                    has_parts = ',' in address_val or len(address_val.split()) > 4
                    has_address = has_pin and has_parts

                device_val = str(data.get('device_id', '')).strip()
                has_device_id = 'device_id' in data and device_val != ''

                ip_val = str(data.get('ip_address', '')).strip()
                has_ip_address = 'ip_address' in data and bool(re.match(r'^(?:\d{1,3}\.){3}\d{1,3}$', ip_val))

                comb_count = sum([has_full_name, has_email, has_address, has_device_id, has_ip_address])

                if comb_count >= 2:
                    is_pii_flag = True
                    if has_full_name:
                        for nk in name_keys_to_redact:
                            if nk in data:
                                redacted_data[nk] = mask_value(nk, str(data[nk]))
                    if has_email and 'email' in data:
                        redacted_data['email'] = mask_value('email', email_val)
                    if has_address and 'address' in data:
                        redacted_data['address'] = mask_value('address', address_val)
                    if has_device_id and 'device_id' in data:
                        redacted_data['device_id'] = mask_value('device_id', device_val)
                    if has_ip_address and 'ip_address' in data:
                        redacted_data['ip_address'] = mask_value('ip_address', ip_val)

                redacted_json = json.dumps(redacted_data, ensure_ascii=False)
                writer.writerow([record_id, redacted_json, is_pii_flag])