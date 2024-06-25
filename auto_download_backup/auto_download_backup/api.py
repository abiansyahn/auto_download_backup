import frappe
import os
import requests
import glob
from datetime import datetime, timedelta

def download_backup():
    settings = frappe.get_single('Auto Download Backup Setting')
    if not settings:
        return
    api_key = settings.api_key
    api_secret = settings.api_secret
    url = settings.frappe_url
    max_file_saved = settings.amount_file_saved
    url_api = url+"/api/method/cloud_backup.cloud_backup.cloud_backup.upload_backup"
    headers = {
        'Authorization': f'token {api_key}:{api_secret}'
    }

    # Get the backup and files from Frappe Cloud
    response = requests.get(url_api, headers=headers)
    if response.status_code == 200:
        data = response.json()["message"]

        #  # Define the new directory
        backup_dir = os.path.join(frappe.get_site_path(), 'live_backup')

        # # Create the directory if it doesn't exist
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # # Save database backup
        backup_file_path = os.path.join(backup_dir, data['backup']['filename'])
        with open(backup_file_path, 'wb') as f:
            f.write(data['backup']['content'].encode('latin1'))

        # # Save public_files.tar
        public_files_tar_path = os.path.join(backup_dir, data['public_files']['filename'])
        with open(public_files_tar_path, 'wb') as f:
            f.write(data['public_files']['content'].encode('latin1'))

        # # Save private_files.tar
        private_files_tar_path = os.path.join(backup_dir, data['private_files']['filename'])
        with open(private_files_tar_path, 'wb') as f:
            f.write(data['private_files']['content'].encode('latin1'))

        # Clean up old files if necessary
        clean_up_old_files(backup_dir, max_file_saved)

        # Update last backup time
        update_last_backup_time()

        return {"status": "success", "message": "Backup and files received successfully"}
    else:
        print("Failed to download backup and files from Frappe Cloud")

def save_file_if_new(directory, filename, content):
    file_path = os.path.join(directory, filename)
    # Check if the file already exists
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content.encode('latin1'))

def clean_up_old_files(directory, max_file_saved):
    # List all files in the directory sorted by modification time
    files = glob.glob(os.path.join(directory, '*'))
    files.sort(key=os.path.getmtime)

    # Calculate the number of files to delete
    num_files_to_delete = len(files) - (max_file_saved * 3)

    # Delete the oldest files if necessary
    for i in range(num_files_to_delete):
        os.remove(files[i])

def get_last_backup_time():
    settings = frappe.get_single('Auto Download Backup Setting')
    return settings.last_backup_time

def update_last_backup_time():
    settings = frappe.get_single('Auto Download Backup Setting')
    settings.last_backup_time = datetime.now()
    settings.save()
    frappe.db.commit()

def schedule_backup():
    settings = frappe.get_single('Auto Download Backup Setting')
    download_time = settings.download_time

    # Convert download_time to seconds
    time_intervals = {
        '1 Week': 7 * 24 * 60 * 60,
        '1 Hour': 60 * 60,
        '2 Hour': 2 * 60 * 60,
        '4 Hour': 4 * 60 * 60,
        '6 Hour': 6 * 60 * 60,
        '8 Hour': 8 * 60 * 60,
        '12 Hour': 12 * 60 * 60,
        '1 Day': 24 * 60 * 60,
        '1 Month': 30 * 24 * 60 * 60
    }

    interval = time_intervals.get(download_time, 60 * 60)  # Default to 1 hour if not found
    last_backup_time = get_last_backup_time()

    if last_backup_time:
        last_backup_time = datetime.strptime(last_backup_time, '%Y-%m-%d %H:%M:%S.%f')
        next_run_time = last_backup_time + timedelta(seconds=interval)
    else:
        next_run_time = datetime.now()

    if datetime.now() >= next_run_time:
        download_backup()

    # Schedule the next check in one hour
    next_check_time = datetime.now() + timedelta(hours=1)
    frappe.enqueue('auto_download_backup.auto_download_backup.api.schedule_backup', enqueue_after_commit=True, execute_after=next_check_time)

if __name__ == "__main__":
    schedule_backup()