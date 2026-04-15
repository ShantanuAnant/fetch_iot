# Fetch IoT Notes

This project downloads IoT lecture notes (as images) for specific chapters and compiles them into a single PDF file.

## Setup

1.  **Install Dependencies**

    Make sure you have Python installed, then run:

    ```bash
    pip install -r fetch_iot/requirements.txt
    ```

## Usage

You can download notes for specific chapters using the following commands:

### For Chapter 1
```bash
python fetch_iot/get_pdf_notes.py --1
```

### For Chapter 2
```bash
python fetch_iot/get_pdf_notes.py --2
```

### For Chapter 3
```bash
python fetch_iot/get_pdf_notes.py --c 3
```

### For Chapter 4
```bash
python fetch_iot/get_pdf_notes.py --4
```

### For Chapter 5
```bash
python fetch_iot/get_pdf_notes.py --5
```