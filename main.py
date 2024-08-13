import streamlit as st
import pandas as pd
import ollama
import ast
import json
import re
import io
from PIL import Image
from streamlit_lottie import st_lottie
import requests

# Function to load Lottie animations
def load_lottie_url(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

welcome_animation = load_lottie_url("https://lottie.host/0bd09814-d2ae-4f38-a301-4b1c01d1d778/OWezBSJvFE.json")
congratulations_animation = load_lottie_url("https://lottie.host/768b23c5-2167-45ed-afb0-42f3fc4d7c0c/F40M6pnGsn.json")

def extract_and_convert_list(text):
    list_match = re.search(r'\[.*?\]', text, re.DOTALL)
    if list_match:
        list_string = list_match.group()
        try:
            python_list = ast.literal_eval(list_string)
            if isinstance(python_list, list):
                return python_list
            else:
                return None
        except (SyntaxError, ValueError):
            return None
    else:
        return None

def extract_and_parse_json(text):
    start_index = text.find('{')
    end_index = text.rfind('}')
    if start_index == -1 or end_index == -1 or end_index < start_index:
        return None, False
    json_str = text[start_index:end_index + 1]
    try:
        parsed_json = json.loads(json_str)
        return parsed_json, True
    except json.JSONDecodeError:
        return None, False

def validate_and_convert_salary_json(json_input):
    def is_valid_salary_comparison(data):
        return (
            "salary_comparison" in data and
            "philippines" in data["salary_comparison"] and
            "united_states" in data["salary_comparison"]
        )
    if isinstance(json_input, dict):
        valid = is_valid_salary_comparison(json_input)
        return json_input, valid
    try:
        data = json.loads(json_input)
        valid = is_valid_salary_comparison(data)
        valid = data["salary_comparison"]["philippines"] < 10000 and data["salary_comparison"]["united_states"] < 10000
        return data, valid
    except (json.JSONDecodeError, TypeError):
        return None, False

def check_input_specificity(input_text):
    generic_phrases = ["general","n/a", "not sure", "don't know", "do you", "are you", "you", "Are there"]
    if any(phrase.lower() in input_text.lower() for phrase in generic_phrases):
        return False
    return True

def simulate_job_relevance_classification(job_list, company_needs_description):
    if not job_list:
        return [], []
    
    relevant_roles = [role for role in job_list if role.lower() not in company_needs_description.lower()]
    irrelevant_roles = [role for role in job_list if role.lower() in company_needs_description.lower()]

    return relevant_roles, irrelevant_roles

def input_is_out_of_context(input_text):
    irrelevant_keywords = ["unrelated", "out of context", "irrelevant"]
    for phrase in irrelevant_keywords:
        if phrase.lower() in input_text.lower():
            return True
    return False

def is_relevant_to_jobs_and_business(input_text):
    relevant_keywords = ["job", "hire", "business", "project", "team", "staff", "company", "role", "position", "expertise"]
    for keyword in relevant_keywords:
        if keyword.lower() in input_text.lower():
            return True
    return False

def analyze_url_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            text = response.text
            about_us_start = text.lower().find('about us', 'our company')
            if about_us_start != -1:
                about_us_end = text.lower().find('</div>', about_us_start)
                about_us_content = text[about_us_start:about_us_end]
                return about_us_content
        else:
            return None
    except Exception as e:
        return None

def team_builder_page():
    # Header and introduction
    col1, col2, col3 = st.columns([2,1.3,2])
    with col1:
        st.write(' ')
    with col2:
        st.image("Connext_Logo.png", width=400)
    with col3:
        st.write(' ')
       
    st_lottie(welcome_animation, height=200, key="welcome_animation")

    st.write("""
    <div style="text-align: center;">
        <h1>Connext Team Builder</h1>
        <p>
        Connext Global Solutions specializes in providing full-service offshore staffing and custom-built team solutions.
        They offer recruiting, payroll, compliance, IT, facilities, and management support to help businesses build high-performing global teams.
        Services cater to various industries and functions, emphasizing customizing teams based on specific client needs.
        Their approach involves assessing, recruiting, training, and managing offshore staff to ensure optimal performance and alignment with client objectives.
        They also provide continuous support and performance monitoring to ensure the offshore team meets and exceeds client expectations. With a focus on cost-efficiency and high-quality talent, Connext Global Solutions enables companies to scale effectively while maintaining control over their operations.
        <a href="https://connextglobal.com/">Connext Global Solutions</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center;">
        <h3>Help Us Help You Find the Right Talent</h3>
        <p>Please describe the challenges, needs, or goals your company is currently facing. For example:</p>
        <ul style="text-align: left; display: inline-block;">
            <li>Are there any specific project bottlenecks?</li>
            <li>What new initiatives are you planning that require additional expertise?</li>
            <li>Do you need recommendations for specific job roles to enhance your team's capabilities?</li>
        </ul>
        <p>Provide as much detail as possible to help us suggest the most suitable job roles and expertise needed for your company. You may also input the job roles you need directly.</p>
    </div>
    """, unsafe_allow_html=True)

    company_needs_description = st.text_area("Enter Description or Paste the Company's URL/About us page to generate job roles:", height=150)
    
    if 'main_response' not in st.session_state:
        st.session_state.main_response = ""
    
    if "job_list" not in st.session_state:
        st.session_state.job_list = []
    
    if "relevant_job_list" not in st.session_state:
        st.session_state.relevant_job_list = []
    
    if "irrelevant_job_list" not in st.session_state:
        st.session_state.irrelevant_job_list = []
    
    if "job_list_salary" not in st.session_state:
        st.session_state.job_list_salary = []
    
    if 'additional_info' not in st.session_state:
        st.session_state.additional_info = ""
    
    if 'show_job_list' not in st.session_state:
        st.session_state.show_job_list = False
    
    if st.button("Analyze"):
        is_url_provided = company_needs_description.startswith("http")
        if is_url_provided:
            about_us_content = analyze_url_content(company_needs_description)
            if about_us_content:
                company_needs_description = about_us_content
            else:
                st.session_state['job_list'] = []
                st.session_state.show_job_list = False
        
        if not is_url_provided and (not check_input_specificity(company_needs_description) or input_is_out_of_context(company_needs_description) or not is_relevant_to_jobs_and_business(company_needs_description)):
            st.warning("Your input is not applicable. Please provide more specific details.")
            st.session_state['job_list'] = []
            st.session_state.show_job_list = False
        else:
            with st.spinner("Analyzing your needs..."):
                chat_log = [
                    {"role": "system", "content": "You are tasked to analyze the job role needs of a company based on the description/queries from the users/company."},
                    {"role": "user", "content": company_needs_description}
                ]
                result = ollama.chat(model="llama3.1", messages=chat_log)
                response = result["message"]["content"]
                
                st.session_state.main_response = response
    
                if "job roles" in response.lower():
                    prompt = """
                        Based on the previous job roles analysis, can you give me the list of the job roles from the previous response and format it into a python list.
                        It should just be a list of strings of the job roles.
    
                        Example:
                        ["Web Developer", "Accountant", "3D graphic artist"]
                    """
                    chat_log = [
                        {"role": "system", "content": "You are an HR manager which extracts the job roles based on a user/company needs analysis."},
                        {"role": "user", "content": company_needs_description},
                        {"role": "assistant", "content": response},
                        {"role": "user", "content": prompt}
                    ]
    
                    result = ollama.chat(model="llama3.1", messages=chat_log)
                    job_list_response = result["message"]["content"]
                    job_list = extract_and_convert_list(job_list_response)
                    if job_list:
                        st.session_state['job_list'] = job_list
                        st.session_state.relevant_job_list, st.session_state.irrelevant_job_list = simulate_job_relevance_classification(job_list, company_needs_description)
                        st.session_state.show_job_list = True
                    else:
                        st.warning("Failed to generate job roles. Please provide more specific details.")
                        st.session_state.show_job_list = False
                else:
                    st.warning("Your input is out of context. Please provide more specific details.")
                    st.session_state['job_list'] = []
                    st.session_state.show_job_list = False
    
                st.experimental_rerun()
    
    if st.session_state.main_response:
        with st.expander("View Response"):
            st.write(st.session_state.main_response)
        
        additional_info = st.text_area("Please add in anything more you like, otherwise just leave it blank:", height=100)
        st.session_state.additional_info = additional_info
    
        if st.button("Submit Additional Info"):
            if additional_info.lower() in ["n/a", "not sure", "don't know", "general"] or not is_relevant_to_jobs_and_business(additional_info):
                st.warning("Your additional info is not applicable. Please provide more specific details.")
                st.session_state['job_list'] = []
                st.session_state.show_job_list = False
            else:
                with st.spinner("Processing additional info..."):
                    full_description = f"{company_needs_description}\n\nAdditional Info: {additional_info}"
                    chat_log = [
                        {"role": "system", "content": "You are tasked to analyze the job role needs of a company based on the description/queries from the users/company."},
                        {"role": "user", "content": full_description}
                    ]
                    result = ollama.chat(model="llama3.1", messages=chat_log)
                    response = result["message"]["content"]
                    
                    st.session_state.main_response = response
    
                    if "job roles" in response.lower():
                        prompt = """
                            Based on the previous job roles analysis, can you give me the list of the job roles from the previous response and format it into a python list.
                            It should just be a list of strings of the job roles.
    
                            Example:
                            ["Web Developer", "Accountant", "3D graphic artist"]
                        """
                        chat_log = [
                            {"role": "system", "content": "You are an HR manager which extracts the job roles based on a user/company needs analysis."},
                            {"role": "user", "content": full_description},
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": prompt}
                        ]
    
                        result = ollama.chat(model="llama3.1", messages=chat_log)
                        job_list_response = result["message"]["content"]
                        job_list = extract_and_convert_list(job_list_response)
                        if job_list:
                            st.session_state['job_list'] = job_list
                            st.session_state.relevant_job_list, st.session_state.irrelevant_job_list = simulate_job_relevance_classification(job_list, full_description)
                            st.session_state.show_job_list = True
                        else:
                            st.warning("Failed to generate job roles. Please provide more specific details.")
                            st.session_state.show_job_list = False
                    else:
                        st.warning("Your additional info is out of context. Please provide more specific details.")
                        st.session_state['job_list'] = []
                        st.session_state.show_job_list = False
    
                st.experimental_rerun()
    
    if st.session_state.show_job_list and st.session_state['job_list']:
        st.markdown("### Job Roles You May Need")
        
        st.markdown("#### Relevant Job Roles")
        relevant_roles_str = ', '.join(st.session_state.relevant_job_list)
        relevant_roles_input = st.text_area("Add or edit relevant job roles (comma-separated):", value=relevant_roles_str, height=100)
        st.session_state.relevant_job_list = [role.strip() for role in relevant_roles_input.split(',')]
    
        st.markdown("#### Irrelevant Job Roles")
        irrelevant_roles_str = ', '.join(st.session_state.irrelevant_job_list)
        irrelevant_roles_input = st.text_area("Add or edit irrelevant job roles (comma-separated):", value=irrelevant_roles_str, height=100)
        st.session_state.irrelevant_job_list = [role.strip() for role in irrelevant_roles_input.split(',')]
    
        if st.button("Proceed"):
            st.session_state.show_job_list = False
    
    if st.session_state.relevant_job_list:
        job_list_salary = []
    
        for job in st.session_state["relevant_job_list"]:
            job_not_parsed_successfully = True
    
            while job_not_parsed_successfully:
                prompt = f"""
                Generate a JSON object that represents the monthly median salary in US Dollars for a specific job role, with comparisons between the Philippines and the United States. Please adhere to the following guidelines:
                - The output must be a JSON object without any comments.
                - All monetary values must be in USD.
                - Salaries should be expressed as whole numbers without commas; ensure they are realistic and below 10000.
                - Typically, salaries in the United States are significantly higher than in the Philippines; please consider this when providing figures.
                - The format of the JSON should strictly follow the structure below:
    
                Here's the job: {job}
    
                Required JSON format:
                {{
                    "salary_comparison": {{
                        "philippines": <number>,
                        "united_states": <number>
                    }}
                }}
                """
    
                chat_log = [
                    {"role": "system", "content": "You are tasked to find salary information from a specific job."},
                    {"role": "user", "content": prompt}
                ]
    
                result = ollama.chat(model="llama3.1", messages=chat_log)
                job_salary_comparison = result["message"]["content"]
    
                salary_comparison_json, salary_comparison_parsed_successfully = extract_and_parse_json(job_salary_comparison)
                
                if salary_comparison_parsed_successfully == False:
                    continue
    
                salary_comparison_json_cleaned, salary_comparison_valid_json = validate_and_convert_salary_json(salary_comparison_json)
    
                if salary_comparison_valid_json == False:
                    continue
    
                job_not_parsed_successfully = False
        
            job_salary = {
                "job_role": job,
                "currency": "USD",
                "salary_comparison": salary_comparison_json_cleaned['salary_comparison']
            }
            job_list_salary.append(job_salary)
            st.session_state["job_list_salary"] = job_list_salary
    
        df = pd.DataFrame(job_list_salary)
        df = pd.concat([df.drop(['salary_comparison'], axis=1), df['salary_comparison'].apply(pd.Series)], axis=1)
    
        col1, col2, col3 = st.columns([1,8,1])
        with col2:
            st.dataframe(df)
    
    if st.session_state['job_list_salary']:
        total_jobs = len(st.session_state['job_list_salary'])
    
        st.markdown("##### Select the number of employees you plan to hire")
    
        columns_per_row = 2
        num_rows = (total_jobs + columns_per_row - 1) // columns_per_row
    
        for i in range(num_rows):
            cols = st.columns(columns_per_row)
            for j in range(columns_per_row):
                job_index = i * columns_per_row + j
                if job_index < total_jobs:
                    job = st.session_state['job_list_salary'][job_index]
                    with cols[j]:
                        st.session_state['job_list_salary'][job_index]["no of employees"] = st.number_input(f"{job['job_role']}:", min_value=0, key=f"num_{job['job_role']}")
    
    if st.session_state["job_list_salary"]:
        if st.button("Calculate Cost"):
            total_jobs = len(st.session_state['job_list_salary'])
    
            st.markdown("##### Cost Calculation")
    
            for i in range(total_jobs):
                st.session_state['job_list_salary'][i]["philippines_total_cost"] = st.session_state['job_list_salary'][i]["no of employees"] * st.session_state['job_list_salary'][i]["salary_comparison"]["philippines"]
                st.session_state['job_list_salary'][i]["united_states_total_cost"] = st.session_state['job_list_salary'][i]["no of employees"] * st.session_state['job_list_salary'][i]["salary_comparison"]["united_states"]
                st.session_state['job_list_salary'][i]["total_savings"] = st.session_state['job_list_salary'][i]["united_states_total_cost"] - st.session_state['job_list_salary'][i]["philippines_total_cost"]
                st.session_state['job_list_salary'][i]["connext_total_cost"] = st.session_state['job_list_salary'][i]["philippines_total_cost"]
        
            df = pd.DataFrame(st.session_state['job_list_salary'])
            df = pd.concat([df.drop(['salary_comparison'], axis=1), df['salary_comparison'].apply(pd.Series)], axis=1)
            st.dataframe(df)
    
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False)
            st.download_button(
                label="Download data as CSV",
                data=buffer,
                file_name='team_builder_report.csv',
                mime='text/csv',
            )
    
            philippines_overall_cost = df["philippines_total_cost"].sum()
            united_states_overall_cost = df["united_states_total_cost"].sum()
            expected_savings = df["total_savings"].sum()
            connext_total_cost = df["philippines_total_cost"].sum()  # Calculate the total cost when hiring through Connext Global Solutions
    
            st.write(f"Philippines Overall Cost: {philippines_overall_cost} USD")
            st.write(f"United States Overall Cost: {united_states_overall_cost} USD")
            st.divider()
            st.write(f"* If you hire all of your employees in the Philippines, the following is your expected savings.")
            st.write(f"Overall Savings: {expected_savings} USD")
            
            st.divider()
    
            # Refined job role list with cost difference and savings information
            st.markdown("### Job Role List with Cost Difference and Savings Information when hiring through Connext Global Solutions")

            refined_df = df[["job_role", "philippines_total_cost", "united_states_total_cost","connext_total_cost", "total_savings"]]
            st.write(refined_df)

            buffer = io.BytesIO()
            refined_df.to_csv(buffer, index=False)
            st.download_button(
                label="Download refined data as CSV",
                data=buffer,
                file_name='refined_team_builder_report.csv',
                mime='text/csv',
            )

            # Add a summary of savings information
            total_philippines_cost = refined_df["philippines_total_cost"].sum()
            total_united_states_cost = refined_df["united_states_total_cost"].sum()
            total_savings = refined_df["total_savings"].sum()

            st.write(f"**Total Cost if Hiring in the Philippines:** ${total_philippines_cost:,.2f}")
            st.write(f"**Total Cost if Hiring in the United States:** ${total_united_states_cost:,.2f}")
            st.write(f"**Total Cost if Hiring through Connext Global Solutions:** ${connext_total_cost:,.2f}")
            st.write(f"**Total Savings if Hiring through Connext Global Solutions:** ${total_savings:,.2f}")

            st.markdown("""
            *By hiring through Connext Global Solutions, you can achieve significant cost savings while maintaining high-quality talent and operational control.*
            """)
            st_lottie(congratulations_animation, height=200, key="congratulations_animation")

