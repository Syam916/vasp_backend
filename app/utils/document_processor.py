import os,re
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from datetime import datetime, timedelta
import pandas as pd
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
os.environ['OPENAI_API_KEY']  = os.getenv('OPENAI_API_KEY')
openai_api_key=os.getenv('OPENAI_API_KEY')

from app.config import Config

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE
EXCEL_TEMPLATE=Config.EXCEL_TEMPLATE
REFERENCE_FOLDER=Config.REFERENCE_FOLDER
Excel_file_path=f"{REFERENCE_FOLDER}/{EXCEL_FILE}"
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_image(image_path):
    try:
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)
            return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None

def process_document(file_path):
    try:
        # Extract text based on file type
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            text = extract_text_from_image(file_path)
        else:
            raise ValueError("Unsupported file format")

        if not text:
            raise ValueError("Failed to extract text from document")

        # Process with LLM
        excel_template_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', 'Reference_files', 'Excel_template', 'queries.xlsx'
        )
        
        extracted_data = process_with_llm(text, excel_template_path)
        return extracted_data

    except Exception as e:
        print(f"Error processing document: {e}")
        raise

def process_with_llm(text, excel_template_path):

    try:
        # Load queries from Excel template
        df = pd.read_excel(excel_template_path)
        queries = df['Name'].tolist()

        # Initialize LangChain components
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(text)

        # Create embeddings and vector store
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_texts(chunks, embeddings)
        retriever = vectorstore.as_retriever()

        # Setup LLM chain
        prompt_template = """
        Based on the following context, answer the question:
        Context: {context}
        Question: {query}
        Answer:"""

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "query"]
        )

        llm = ChatOpenAI(temperature=0)
        chain = LLMChain(llm=llm, prompt=prompt)

        # Process each query
        results = {}
        for query in queries:
            relevant_docs = retriever.get_relevant_documents(query)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            answer = chain.run({"context": context, "query": query})
            results[query] = answer

        return results

    except Exception as e:
        print(f"Error in LLM processing: {e}")
        raise 



def extract_text_line_by_line(text):
    """
    Process text line by line to extract and store it.
    :param text: Text to process.
    :return: Processed text line by line.
    """
    lines = text.splitlines()
    processed_lines = "\n".join(line.strip() for line in lines if line.strip())
    return processed_lines

def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    :param image_path: Path to the image file.
    :return: Extracted text line by line.
    """
    try:
        with Image.open(image_path) as img:
            raw_text = pytesseract.image_to_string(img)
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            structured_text = "\n".join(lines)
            return structured_text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def extract_text_from_pdf(pdf_path, output_folder):
    """
    Extract text from a PDF, including flattening it if necessary.
    :param pdf_path: Path to the PDF file.
    :param output_folder: Folder to store intermediate images if needed.
    :return: Extracted text line by line.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"

        if not text.strip():
            images = convert_from_path(pdf_path)
            for i, img in enumerate(images):
                img_path = os.path.join(output_folder, f"page_{i + 1}.png")
                img.save(img_path, "PNG")
                raw_text = extract_text_from_image(img_path)
                text += raw_text + "\n"

        return extract_text_line_by_line(text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""





def answer_queries_from_file_with_prompt(file_path, excel_path, output_column="Answer"):
    """
    Answer multiple queries using a text file as the knowledge base with FAISS, OpenAI, and LangChain.

    Args:1q
        file_path (str): Path to the text file.
        excel_path (str): Path to the Excel file containing the queries.
        output_column (str): The column name to store answers in the Excel sheet.

    Returns:
        None: Saves the answers back to the Excel file.
    """
    # Step 1: Load and chunk the text file
    loader = TextLoader(file_path, encoding='utf-8')  # Specify the encoding
    documents = loader.load()

    # Step 2: Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    # Step 3: Create a vector database with FAISS
    # Explicitly configure OpenAI embeddings without proxies
    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_api_key
    )
    vector_store = FAISS.from_documents(docs, embeddings)

    # Step 4: Define a prompt template for concise answers
    prompt_template = """
    "You are a highly precise and concise assistant. "
    "Answer the following question based, and return the exact and concise response without any additional explanation., dont repeat the question in answer "

    Context: {context}
    Query: {query}
    Answer:
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "query"])

    # Step 5: Initialize the ChatOpenAI model and LLMChain
    chat_model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # Use the chat model
    chain = LLMChain(llm=chat_model, prompt=prompt)

    # Step 6: Read questions from the Excel file
    df = pd.read_excel(excel_path)
    if "Query" not in df.columns:
        raise ValueError("The Excel file must contain a 'Query' column.")

    queries = df["Query"].tolist()

    # Step 7: Process each query and store the answers
    answers = []
    retriever = vector_store.as_retriever()
    for query in queries:
        # Retrieve relevant documents for the current query
        relevant_docs = retriever.get_relevant_documents(query)

        # Combine the retrieved documents into a single context
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        # Run the chain with the current query and context
        answer = chain.run({"context": context, "query": query})
        print(answer)
        answers.append(answer)

    # Step 8: Save answers to the Excel file
    df[output_column] = answers
    df.to_excel(excel_path, index=False)

    print(f"Answers saved to column '{output_column}' in the Excel file.")


def read_excel_and_display():
    """
    Read the Excel file and return data for rendering.
    """
    try:
        df = pd.read_excel(Excel_file_path)
        data = df.to_dict(orient="records")
        return data
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []




def standardize_date(date_str):
    """
    Convert various date string formats to a standard datetime object.
    Returns None if the date string cannot be parsed.
    """
    # Remove any leading/trailing whitespace and common prefixes
    date_str = str(date_str).strip()
    # Remove prefix if it exists (e.g., "The order date is ")
    if "The order date is " in date_str:
        date_str = date_str.replace("The order date is ", "")
    
    # List of possible date formats
    date_formats = [
        # Standard formats
        "%d/%m/%Y",          # 24/01/2021
        "%Y-%m-%d",          # 2024-12-23
        "%d-%m-%Y",          # 23-12-2024
        "%Y/%m/%d",          # 2024/12/23
        "%d.%m.%Y",          # 23.12.2024
        "%Y.%m.%d",          # 2024.12.23
        
        # With time
        "%Y-%m-%d %H:%M:%S",  # 2024-12-23 14:30:00
        "%d-%m-%Y %H:%M:%S",  # 23-12-2024 14:30:00
        "%Y/%m/%d %H:%M:%S",  # 2024/12/23 14:30:00
        "%d/%m/%Y %H:%M:%S",  # 23/12/2024 14:30:00
        "%d.%m.%Y %H:%M:%S",  # 23.12.2024 14:30:00
        
        # Month name formats
        "%d %b %Y",          # 23 Dec 2024
        "%d %B %Y",          # 23 December 2024
        "%b %d, %Y",         # Dec 23, 2024
        "%B %d, %Y",         # December 23, 2024
        
        # American format
        "%m/%d/%Y",          # 12/23/2024
        "%m-%d-%Y",          # 12-23-2024
        "%m.%d.%Y",          # 12.23.2024
    ]
    
    # Clean the date string - remove periods at the end and any extra whitespace
    date_str = date_str.rstrip('.')
    date_str = date_str.strip()
    
    # Try to parse the date string using the defined formats
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try to handle special cases with regex
    # Handle ISO format with timezone
    iso_pattern = r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?([+-]\d{2}:?\d{2}|Z)?'
    iso_match = re.match(iso_pattern, date_str)
    if iso_match:
        try:
            date_part = iso_match.group(1)
            return datetime.strptime(date_part, '%Y-%m-%d')
        except ValueError:
            pass
            
    # If all parsing attempts fail, try to extract date using regex
    date_pattern = r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})'
    match = re.search(date_pattern, date_str)
    if match:
        day, month, year = match.groups()
        # Handle two-digit years
        if len(year) == 2:
            year = '20' + year
        try:
            return datetime(int(year), int(month), int(day))
        except ValueError:
            pass
    
    return None


import subprocess
import os
from pathlib import Path
import tempfile

def upload_to_s3_cli(file_path, user_name,bucket_name='vasp-pdf-files', region='us-east-1'):
    """
    Upload a file to S3 using AWS CLI commands through Python
    
    Parameters:
    file_path (str): Path to the file to upload
    bucket_name (str): Name of the S3 bucket
    region (str): AWS region name
    
    Returns:
    bool: True if file was uploaded successfully, False otherwise
    """
    try:
        # Convert file path to Path object for better path handling
        file_path= "uploads/"+file_path
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Error: File {file_path} not found======================================================")
            return False
            
        # Get the file name from the path
        file_name = f"{user_name}_{file_path.name}"
        
        # Construct the AWS CLI command
        aws_command = [
            'aws', 's3', 'cp',
            str(file_path),
            f's3://{bucket_name}/{file_name}',
            '--region', region
        ]
        
        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            print(f"Successfully uploaded {file_name} to {bucket_name}")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"Error uploading file: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def verify_aws_cli():
    """
    Verify that AWS CLI is installed and configured
    
    Returns:
    bool: True if AWS CLI is available and configured, False otherwise
    """
    try:
        # Check if AWS CLI is installed
        version_check = subprocess.run(
            ['aws', '--version'],
            capture_output=True,
            text=True
        )
        
        if version_check.returncode != 0:
            print("AWS CLI is not installed. Please install it first.")
            return False
            
        # Check if AWS CLI is configured
        configure_check = subprocess.run(
            ['aws', 'configure', 'list'],
            capture_output=True,
            text=True
        )
        
        if configure_check.returncode != 0:
            print("AWS CLI is not configured. Please run 'aws configure' first.")
            return False
            
        return True
        
    except FileNotFoundError:
        print("AWS CLI is not installed. Please install it first.")
        return False


def download_file_from_s3(bucket_name, file_name, region='us-east-1'):
    """
    Download a file from S3 to a local temporary directory and return its local path.
    """
    try:
        # Create a temporary file path
        temp_dir = tempfile.gettempdir()
        local_path = Path(temp_dir) / file_name

        # AWS CLI command to download
        aws_command = [
            'aws', 's3', 'cp',
            f's3://{bucket_name}/{file_name}',
            str(local_path),
            '--region', region
        ]

        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )

        # Check if the command succeeded
        if result.returncode == 0:
            print(f"File downloaded successfully to {local_path}")
            return str(local_path)
        else:
            raise Exception(f"Download failed: {result.stderr}")

    except Exception as e:
        raise Exception(f"Error downloading file: {str(e)}")

    finally:
        # Clean up temporary file on exit if necessary
        if 'local_path' in locals() and os.path.exists(local_path):
            try:
                os.remove(local_path)
                print(f"Temporary file {local_path} cleaned up.")
            except Exception as cleanup_error:
                print(f"Error cleaning up file: {cleanup_error}")

def download_from_s3_cli(user_name, file_name, bucket_name='vasp-pdf-files', region='us-east-1'):
    """
    Download a file from S3 using AWS CLI commands
    
    Parameters:
    user_name (str): Username to construct the full file name
    file_name (str): Name of the file to download
    bucket_name (str): Name of the S3 bucket
    region (str): AWS region name
    
    Returns:
    str: Path to the downloaded file, or None if download fails
    """
    try:
        # Create a temporary directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        
        # Construct the full S3 file name (including username prefix)
        s3_file_name = f"{user_name}_{file_name}"

        print(s3_file_name)
        
        # Create local file path
        local_path = Path(temp_dir) / file_name
        
        # Construct the AWS CLI command
        aws_command = [
            'aws', 's3', 'cp',
            f's3://{bucket_name}/{s3_file_name}',
            str(local_path),
            '--region', region
        ]
        
        # Execute the AWS CLI command
        result = subprocess.run(
            aws_command,
            capture_output=True,
            text=True
        )
        
        # Check if the command was successful
        if result.returncode == 0:
            print(f"Successfully downloaded {s3_file_name}")
            return str(local_path)
        else:
            print(f"Error downloading file: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
