from django.test import TestCase, Client, LiveServerTestCase
from django.urls import reverse
from core.models import ColumnDefinition, ProcessingJob
import json
from django.contrib.auth.models import User
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import os
from selenium.common.exceptions import TimeoutException
import time
import requests
from selenium.webdriver.support.ui import Select

# Module level variable to track Selenium availability
selenium_available = False

class ColumnDefinitionTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create some test columns
        self.column1 = ColumnDefinition.objects.create(
            name='test_column1',
            description='Test Column 1',
            category='demographics',
            order=1,
            include_confidence=True
        )
        self.column2 = ColumnDefinition.objects.create(
            name='test_column2',
            description='Test Column 2',
            category='presentation',
            order=2,
            include_confidence=False
        )

    def test_column_list_view(self):
        """Test the column definition list view"""
        response = self.client.get(reverse('core:columns'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'column_definition.html')
        self.assertContains(response, 'test_column1')
        self.assertContains(response, 'test_column2')

    def test_add_column(self):
        """Test adding a new column"""
        new_column_data = {
            'name': 'new_column',
            'description': 'New Test Column',
            'category': 'demographics',
            'order': 3,
            'include_confidence': True
        }
        response = self.client.post(
            reverse('core:save_columns'),
            data=json.dumps({'columns': [new_column_data]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ColumnDefinition.objects.filter(name='new_column').exists())

    def test_update_column(self):
        """Test updating an existing column"""
        updated_data = {
            'id': self.column1.id,
            'name': 'test_column1',
            'description': 'Updated Description',
            'category': 'demographics',
            'order': 1,
            'include_confidence': True
        }
        response = self.client.post(
            reverse('core:save_columns'),
            data=json.dumps({'columns': [updated_data]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        updated_column = ColumnDefinition.objects.get(id=self.column1.id)
        self.assertEqual(updated_column.description, 'Updated Description')

    def test_delete_column(self):
        """Test deleting a column"""
        response = self.client.post(
            reverse('core:delete_column', kwargs={'pk': self.column1.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ColumnDefinition.objects.filter(id=self.column1.id).exists())

    def test_duplicate_column_name(self):
        """Test attempting to create a column with a duplicate name"""
        duplicate_data = {
            'name': 'test_column1',  # This name already exists
            'description': 'Duplicate Column',
            'category': 'demographics',
            'order': 3,
            'include_confidence': True
        }
        response = self.client.post(
            reverse('core:save_columns'),
            data=json.dumps({'columns': [duplicate_data]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.json()['error'])

    def test_update_column_order(self):
        """Test updating column order"""
        order_data = [
            {'id': self.column1.id, 'order': 2},
            {'id': self.column2.id, 'order': 1}
        ]
        response = self.client.post(
            reverse('core:update_column_order'),
            data=json.dumps(order_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ColumnDefinition.objects.get(id=self.column1.id).order, 2)
        self.assertEqual(ColumnDefinition.objects.get(id=self.column2.id).order, 1)

    def test_validate_column_name(self):
        """Test column name validation"""
        # Test valid name
        response = self.client.post(
            reverse('core:validate_column_name'),
            {'name': 'valid_column_name'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])

        # Test invalid name
        response = self.client.post(
            reverse('core:validate_column_name'),
            {'name': '1invalid_name'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])

    def test_bulk_save_columns(self):
        """Test bulk saving of columns"""
        # Clear existing columns
        ColumnDefinition.objects.all().delete()
        
        bulk_data = {
            'columns': [
                {
                    'name': 'bulk_column1',
                    'description': 'Bulk Column 1',
                    'category': 'demographics',
                    'order': 1,
                    'include_confidence': True
                },
                {
                    'name': 'bulk_column2',
                    'description': 'Bulk Column 2',
                    'category': 'presentation',
                    'order': 2,
                    'include_confidence': False
                }
            ]
        }
        response = self.client.post(
            reverse('core:save_columns'),
            data=json.dumps(bulk_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ColumnDefinition.objects.count(), 2)
        self.assertTrue(ColumnDefinition.objects.filter(name='bulk_column1').exists())
        self.assertTrue(ColumnDefinition.objects.filter(name='bulk_column2').exists())

class ColumnDefinitionJavaScriptTests(LiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("Starting Selenium setup...")
        try:
            # Install ChromeDriver if needed
            print(f"ChromeDriver installed at: {chromedriver_autoinstaller.install()}")
            
            # Configure Chrome options
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            print("Chrome options configured")
            
            # Initialize Chrome driver
            cls.selenium = webdriver.Chrome(options=chrome_options)
            cls.selenium.implicitly_wait(10)
            print("Chrome driver initialized")
            
            # Test that browser loads
            cls.selenium.get('about:blank')
            print("Browser test page loaded successfully")
            
            # Create a test column to ensure we have data
            cls.column = ColumnDefinition.objects.create(
                name='test_column1',
                description='Test Description',
                category='demographics',
                order=1,
                include_confidence=True
            )
            
            cls.selenium_available = True
            
        except Exception as e:
            print(f"Error in Selenium setup: {str(e)}")
            cls.selenium_available = False
            raise unittest.SkipTest(f"Selenium tests skipped due to setup error: {str(e)}")

    def setUp(self):
        super().setUp()
        if not self.selenium_available:
            self.skipTest("Selenium is not available")
        
        # Wait for test server to be ready
        self.wait = WebDriverWait(self.selenium, 10)
        start_time = time.time()
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Try to connect to the test server
                self.selenium.get(self.live_server_url)
                break
            except Exception as e:
                print(f"Waiting for server (attempt {retry_count + 1}/{max_retries}): {str(e)}")
                time.sleep(1)
                retry_count += 1
        else:
            raise Exception("Test server not ready after 30 seconds")

    def test_add_column_ui(self):
        print("\nStarting test_add_column_ui")
        try:
            # Navigate to columns page
            self.selenium.get(f'{self.live_server_url}{reverse("core:columns")}')
            print("Navigated to columns page")
            
            # Wait for the page to load and verify existing column
            self.wait.until(EC.presence_of_element_located((By.ID, "columns-table")))
            print("Found columns table")
            
            # Click the "Add Column" button
            add_button = self.wait.until(EC.element_to_be_clickable((By.ID, "add-column-button")))
            add_button.click()
            print("Clicked add column button")
            
            # Wait for the modal to appear
            self.wait.until(EC.presence_of_element_located((By.ID, "columnModal")))
            print("Modal appeared")
            
            # Fill in the form
            name_input = self.selenium.find_element(By.ID, "id_name")
            name_input.send_keys("new_test_column")
            
            description_input = self.selenium.find_element(By.ID, "id_description")
            description_input.send_keys("New Test Column Description")
            
            category_select = Select(self.selenium.find_element(By.ID, "id_category"))
            category_select.select_by_value("demographics")
            print("Form filled")
            
            # Submit the form
            submit_button = self.selenium.find_element(By.CSS_SELECTOR, "#columnModal .btn-primary")
            submit_button.click()
            print("Form submitted")
            
            # Wait for the new column to appear in the table
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'new_test_column')]")))
            print("New column appeared in table")
            
            # Verify the new column exists
            new_column = ColumnDefinition.objects.filter(name="new_test_column").first()
            self.assertIsNotNone(new_column)
            self.assertEqual(new_column.description, "New Test Column Description")
            self.assertEqual(new_column.category, "demographics")
            print("Column verified in database")
            
        except Exception as e:
            print(f"Error in test_add_column_ui: {str(e)}")
            raise

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'selenium'):
            try:
                cls.selenium.quit()
                print("Selenium browser closed successfully")
            except Exception as e:
                print(f"Error closing Selenium browser: {str(e)}")
        super().tearDownClass()

    @unittest.skipUnless(lambda self: self.is_selenium_available, "Selenium not available")
    def test_edit_column_ui(self):
        """Test editing a column through the UI"""
        try:
            # Create a test column
            column = ColumnDefinition.objects.create(
                name='edit_test',
                description='Original Description',
                category='demographics',
                order=1
            )
            
            # Navigate to columns page
            self.selenium.get(f'{self.live_server_url}{reverse("core:columns")}')
            
            # Get CSRF token from the page
            csrf_token = self.selenium.find_element(By.NAME, 'csrfmiddlewaretoken').get_attribute('value')
            
            # Add CSRF token to request headers
            self.selenium.execute_script(
                'var meta = document.createElement("meta"); '
                'meta.name = "csrf-token"; '
                f'meta.content = "{csrf_token}"; '
                'document.head.appendChild(meta);'
            )
            
            # Wait for and click edit button
            edit_button = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//tr[@data-column-id='{column.id}']//button[contains(@class, 'edit-row')]")
                )
            )
            edit_button.click()
            
            # Wait for edit form to appear
            description_input = WebDriverWait(self.selenium, 10).until(
                EC.presence_of_element_located((By.NAME, "description"))
            )
            
            # Clear and update description
            description_input.clear()
            description_input.send_keys("Updated Description")
            
            # Submit form
            submit_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            # Handle any alert that might appear
            try:
                WebDriverWait(self.selenium, 3).until(EC.alert_is_present())
                alert = self.selenium.switch_to.alert
                alert_text = alert.text
                alert.accept()
                print(f"Alert appeared with text: {alert_text}")
                if "error" in alert_text.lower():
                    raise Exception(f"Server error occurred: {alert_text}")
            except TimeoutException:
                pass  # No alert appeared, which is expected
            
            # Wait for update to complete and verify
            def description_is_updated(driver):
                try:
                    column.refresh_from_db()
                    return column.description == "Updated Description"
                except Exception:
                    return False
            
            WebDriverWait(self.selenium, 10).until(description_is_updated)
            
        except Exception as e:
            print(f"Error in test_edit_column_ui: {str(e)}")
            raise

    @unittest.skipUnless(lambda self: self.is_selenium_available, "Selenium not available")
    def test_delete_column_ui(self):
        """Test deleting a column through the UI"""
        try:
            # Create a test column
            column = ColumnDefinition.objects.create(
                name='delete_test',
                description='Test Description',
                category='demographics',
                order=1
            )
            
            # Navigate to columns page
            self.selenium.get(f'{self.live_server_url}{reverse("core:columns")}')
            
            # Get CSRF token from the page
            csrf_token = self.selenium.find_element(By.NAME, 'csrfmiddlewaretoken').get_attribute('value')
            
            # Add CSRF token to request headers
            self.selenium.execute_script(
                'var meta = document.createElement("meta"); '
                'meta.name = "csrf-token"; '
                f'meta.content = "{csrf_token}"; '
                'document.head.appendChild(meta);'
            )
            
            # Wait for and click delete button
            delete_button = WebDriverWait(self.selenium, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//tr[@data-column-id='{column.id}']//button[contains(@class, 'delete-row')]")
                )
            )
            delete_button.click()
            
            # Accept the confirmation dialog
            WebDriverWait(self.selenium, 10).until(EC.alert_is_present())
            alert = self.selenium.switch_to.alert
            alert.accept()
            
            # Wait for deletion to complete
            def column_is_deleted(driver):
                try:
                    return not ColumnDefinition.objects.filter(id=column.id).exists()
                except Exception:
                    return False
            
            WebDriverWait(self.selenium, 10).until(column_is_deleted)
            
        except Exception as e:
            print(f"Error in test_delete_column_ui: {str(e)}")
            raise 