import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# Initialize Chrome WebDriver using webdriver-manager to handle driver version
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

try:
    # Open the webpage
    driver.get("https://results.eci.gov.in/")

    # Increase the timeout to 20 seconds for WebDriverWait
    wait = WebDriverWait(driver, 20)

    # Wait for the element to be present and clickable
    state_item = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".state-item.blue-bg.pc-wrap")))

    # Click on the element
    state_item.click()

    # Wait for the new page or tab to open
    time.sleep(2)  # Adjust the sleep time if necessary

    # Get the handle of the current window
    main_window = driver.current_window_handle

    # Get all window handles
    window_handles = driver.window_handles

    # Switch to the new window if it is different from the main window
    for handle in window_handles:
        if handle != main_window:
            driver.switch_to.window(handle)
            break

    # Now you are on the new page
    # Locate the scrollable table and extract its contents as before
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "child-scroll")))
    table = driver.find_element(By.CLASS_NAME, "child-scroll")
    table_head = table.find_element(By.CLASS_NAME, "table-responsive").find_element(By.TAG_NAME, "thead")
    table_body = table.find_element(By.CLASS_NAME, "table-responsive").find_element(By.TAG_NAME, "tbody")

    headers = [th.text for th in table_head.find_elements(By.TAG_NAME, "th")]

    rows = []
    for tr in table_body.find_elements(By.TAG_NAME, "tr"):
        cells = [td.text for td in tr.find_elements(By.TAG_NAME, "td")]
        rows.append(cells)

    partywise_df = pd.DataFrame(rows, columns=headers)
    partywise_df.to_csv("partywise_data.csv", index=False)

    # Find the state dropdown
    state_dropdown = None

    while True:
        try:
            state_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Result1_ddlState"))
            break  # Exit the loop if found
        except:
            pass  # Continue the loop if not found

    statewise_data = []
    statewise_party_data = []
    detailed_constituency_data = []

    # Loop through each state option
    for i in range(len(state_dropdown.options)):
        try:
            # Re-locate the state dropdown element within the loop
            state_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Result1_ddlState"))
            option = state_dropdown.options[i]
            value = option.get_attribute("value")
            if value.startswith("U") or value.startswith("S"):
                # Select the state
                state_dropdown.select_by_value(value)

                # Wait for the page to refresh and load new data
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-title")))

                # Extract state name and number of PCs
                state_title = driver.find_element(By.CLASS_NAME, "page-title").find_element(By.TAG_NAME, "h2")
                state_name = state_title.find_element(By.TAG_NAME, "strong").text.strip()
                no_of_pcs_text = state_title.find_element(By.TAG_NAME, "span").text.strip()
                
                # Use regex to extract the number of PCs
                match = re.search(r'\bTotal PC - (\d+)\b', no_of_pcs_text)
                if match:
                    no_of_pcs = int(match.group(1))
                else:
                    no_of_pcs = 0  # Default value if pattern not found

                statewise_data.append({"state_name": state_name, "no_of_pcs": no_of_pcs})

                # Wait for the main results table to be present
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))

                # Extract the table data
                results_table = driver.find_element(By.CLASS_NAME, "table")
                results_body = results_table.find_element(By.TAG_NAME, "tbody")
                
                for row in results_body.find_elements(By.TAG_NAME, "tr"):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        party = cells[0].text.strip()
                        won = cells[1].text.strip()
                        leading = cells[2].text.strip()
                        total = cells[3].text.strip()
                        statewise_party_data.append({
                            "state": state_name,
                            "party": party,
                            "won": won,
                            "leading": leading,
                            "total": total
                        })
                
                # Handle constituency dropdown and extract detailed data
                constituency_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Result1_ddlState"))
                for j in range(1, len(constituency_dropdown.options)):
                    constituency_dropdown = Select(driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_Result1_ddlState"))
                    constituency_option = constituency_dropdown.options[j]
                    constituency_text = constituency_option.text.strip()
                    constituency_name = constituency_text.split(" - ")[0]
                    constituency_dropdown.select_by_index(j)

                    # Wait for the page to load
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "switch-list")))
                    
                    # Click on the 2nd list item to load the new table
                    switch_list = driver.find_element(By.CLASS_NAME, "switch-list")
                    switch_list.find_elements(By.TAG_NAME, "li")[1].click()

                    # Wait for the new table to be present
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))

                    # Extract detailed table data
                    detailed_table = driver.find_element(By.CLASS_NAME, "table.table-striped.table-bordered")
                    detailed_body = detailed_table.find_element(By.TAG_NAME, "tbody")
                    
                    for row in detailed_body.find_elements(By.TAG_NAME, "tr"):
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 5:
                            candidate = cells[1].text.strip()
                            party = cells[2].text.strip()
                            evm_votes = cells[3].text.strip()
                            postal_votes = cells[4].text.strip()
                            total_votes = cells[5].text.strip()
                            percentage_votes = cells[6].text.strip()
                            detailed_constituency_data.append({
                                "state_name": state_name,
                                "constituency_name": constituency_name,
                                "candidate": candidate,
                                "party": party,
                                "evm_votes": evm_votes,
                                "postal_votes": postal_votes,
                                "total_votes": total_votes,
                                "percentage_votes": percentage_votes
                            })

                    # Go back 2 pages
                    driver.back()
                    driver.back()

                driver.back()

        except Exception as e:
            print(f"Error processing state option {option.get_attribute('innerText')}: {str(e)}")

    # Create DataFrame for statewise data
    statewise_df = pd.DataFrame(statewise_data, columns=["state_name", "no_of_pcs"])
    print("Statewise DataFrame:")
    print(statewise_df)

    # Create DataFrame for statewise party data
    statewise_party_df = pd.DataFrame(statewise_party_data, columns=["state", "party", "won", "leading", "total"])
    print("Statewise Party DataFrame:")
    print(statewise_party_df)

    # Create DataFrame for detailed constituency data
    detailed_constituency_df = pd.DataFrame(detailed_constituency_data, columns=["state_name", "constituency_name", "candidate", "party", "evm_votes", "postal_votes", "total_votes", "percentage_votes"])
    print("Detailed Constituency DataFrame:")
    print(detailed_constituency_df)
    
    statewise_df.to_csv("statewise_data.csv", index=False)
    statewise_party_df.to_csv("statewise_party_data.csv", index=False)
    detailed_constituency_df.to_csv("detailed_constituency_data.csv", index=False)
finally:
    # Close the WebDriver
    driver.quit()
