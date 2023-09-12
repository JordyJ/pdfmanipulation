# Import Libraries
import argparse
import os
import re
from io import BytesIO
from typing import Tuple

import fitz
import pandas as pd


def extract_info(input_file: str):
    """
    Extracts file info
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    output = {
        "File": input_file,
        "Encrypted": ("True" if pdfDoc.isEncrypted else "False"),
    }
    # If PDF is encrypted the file metadata cannot be extracted
    if not pdfDoc.isEncrypted:
        for key, value in pdfDoc.metadata.items():
            output[key] = value

    # To Display File Info
    print("## File Information ##################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in output.items()))
    print("######################################################################")

    return True, output


def search_for_text(lines, search_str):
    """
    Search for the search string within the document lines
    """
    for line in lines:
        # Find all matches within one line
        results = re.findall(search_str, line, re.IGNORECASE)
        # In case multiple matches within one line
        for result in results:
            yield result


def redact_matching_data(page, matched_values):
    """
    Redacts matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        # Redact matching values
        [
            page.add_redact_annot(area, text=" ", fill=(0, 0, 0))
            for area in matching_val_area
        ]
    # Apply the redaction
    page.apply_redactions()
    return matches_found


def frame_matching_data(page, matched_values):
    """
    frames matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        for area in matching_val_area:
            if isinstance(area, fitz.fitz.Rect):
                # Draw a rectangle around matched values
                annot = page.add_rect_annot(area)
                # , fill = fitz.utils.getColor('black')
                annot.setColors(stroke=fitz.utils.getColor("red"))
                # If you want to remove matched data
                # page.addFreetext_annot(area, ' ')
                annot.update()
    return matches_found


def highlight_matching_data(page, matched_values, type, color="red"):
    """
    Highlight matching values
    """
    matches_found = 0
    # Loop throughout matching values
    for val in matched_values:
        matches_found += 1
        matching_val_area = page.search_for(val)
        # print("matching_val_area",matching_val_area)
        highlight = None
        if type == "Highlight":
            highlight = page.add_highlight_annot(matching_val_area)
        elif type == "Squiggly":
            highlight = page.add_squiggly_annot(matching_val_area)
        elif type == "Underline":
            highlight = page.add_underline_annot(matching_val_area)
        elif type == "Strikeout":
            highlight = page.add_strikeout_annot(matching_val_area)
        elif type == "FreeText":
            highlight = page.add_freetext_annot(
                rect=matching_val_area[0],
                text="",
                fill_color=fitz.utils.getColor("blue"),
            )

        else:
            highlight = page.add_highlight_annot(matching_val_area)
        highlight.set_colors(stroke=fitz.utils.getColor(color))

        highlight.update()
        break
    return matches_found


def extract_context(
    input_file: str, search_str: str, pages: Tuple = None, context_size="5"
):
    # Extracts the context of the search string e.g. the surrounding paragraphs

    pdfDoc = fitz.open(input_file)
    # Save the generated PDF to memory buffer
    BytesIO()

    found_strings = []
    # Iterate through pages
    for pg in range(pdfDoc.page_count):
        # If required for specific pages
        if pages:
            if str(pg) not in pages:
                continue

        # Select the page
        page = pdfDoc[pg]
        # Get Matching Data
        # Split page by lines
        page_text = page.get_text("text")

        # Regex to find the search string and the surrounding paragraphs
        regex_str = (
            r"((?:\n.+){0,context_size}" + search_str + r"(?:.+\n){0,context_size})"
        )
        regex_str = regex_str.replace("context_size", context_size)
        hits = re.findall(
            regex_str,
            page_text,
        )

        print(f"Page {pg+1} had {len(hits)} hits.")
        # hits = re.findall(search_str, page_text)

        # clean the hits
        hits = [hit.replace("-\n", "") for hit in hits]
        hits = [hit.replace("\n", " ") for hit in hits]

        # zip the hits with the page number
        hits = list(zip([pg + 1] * len(hits), hits))

        # print(hits)
        found_strings.extend(hits)

    pdfDoc.close()

    return found_strings


def process_data(
    input_file: str,
    output_file: str,
    search_str: str,
    pages: Tuple = None,
    action: str = "Highlight",
    color: str = "yellow",
    **kwargs,
):
    """
    Process the pages of the PDF File
    """
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    # Save the generated PDF to memory buffer
    output_buffer = BytesIO()
    total_matches = 0
    # Iterate through pages
    for pg in range(pdfDoc.page_count):
        # If required for specific pages
        if pages:
            if str(pg) not in pages:
                continue
        # Select the page
        page = pdfDoc[pg]
        # Get Matching Data
        # Split page by lines
        page_lines = page.get_text("text").split("\n")

        matched_values = search_for_text(page_lines, search_str)
        if matched_values:
            if action == "Redact":
                matches_found = redact_matching_data(page, matched_values)
            elif action == "Frame":
                matches_found = frame_matching_data(page, matched_values)
            elif action in (
                "Highlight",
                "Squiggly",
                "FreeText",
                "Underline",
                "Strikeout",
            ):
                matches_found = highlight_matching_data(
                    page, matched_values, action, color=color
                )
            else:
                matches_found = highlight_matching_data(
                    page, matched_values, "Highlight", color=color
                )
            total_matches += matches_found
    print(
        f"{total_matches} Match(es) Found of Search String "
        // +f"'{search_str}' In Input File: {input_file}"
    )
    # Save to output
    pdfDoc.save(output_buffer)
    pdfDoc.close()
    # Save the output buffer to the output file
    with open(output_file, mode="wb") as f:
        f.write(output_buffer.getbuffer())


def remove_highlght(input_file: str, output_file: str, pages: Tuple = None):
    # Open the PDF
    pdfDoc = fitz.open(input_file)
    # Save the generated PDF to memory buffer
    output_buffer = BytesIO()
    # Initialize a counter for annotations
    annot_found = 0
    # Iterate through pages
    for pg in range(pdfDoc.page_count):
        # If required for specific pages
        if pages:
            if str(pg) not in pages:
                continue
        # Select the page
        page = pdfDoc[pg]
        annot = page.first_annot
        while annot:
            annot_found += 1
            page.delete_annot(annot)
            annot = annot.next
    if annot_found >= 0:
        print(f"Annotation(s) Found In The Input File: {input_file}")
    # Save to output
    pdfDoc.save(output_buffer)
    pdfDoc.close()
    # Save the output buffer to the output file
    with open(output_file, mode="wb") as f:
        f.write(output_buffer.getbuffer())


def process_file(**kwargs):
    """
    To process one single file
    Redact, Frame, Highlight... one PDF File
    Remove Highlights from a single PDF File
    """
    input_file = kwargs.get("input_file")
    output_file = kwargs.get("output_file")
    if output_file is None:
        output_file = input_file
    search_str = kwargs.get("search_str")
    pages = kwargs.get("pages")
    # Redact, Frame, Highlight, Squiggly, Underline, Strikeout, Remove
    action = kwargs.get("action")
    color = kwargs.get("color")

    if action == "Remove":
        # Remove the Highlights except Redactions
        remove_highlght(input_file=input_file, output_file=output_file, pages=pages)
        return None
    elif action == "Extract Context":
        # Remove the Highlights except Redactions
        hits = extract_context(
            input_file=input_file,
            search_str=search_str,
            pages=pages,
            context_size=kwargs.get("context_size"),
        )

        print("context size", kwargs.get("context_size"))
        return {"filename": input_file, "search_str": search_str, "hits": hits}
    else:
        process_data(
            input_file=input_file,
            output_file=output_file,
            search_str=search_str,
            pages=pages,
            action=action,
            color=color,
        )
        return None


def process_folder(**kwargs):
    """
    Redact, Frame, Highlight... all PDF Files within a specified path
    Remove Highlights from all PDF Files within a specified path
    """
    input_folder = kwargs.get("input_folder")
    search_str = kwargs.get("search_str")
    # Run in recursive mode
    recursive = kwargs.get("recursive")
    # Redact, Frame, Highlight, Squiggly, Underline, Strikeout, Remove
    action = kwargs.get("action")
    pages = kwargs.get("pages")
    color = kwargs.get("color")
    context_size = kwargs.get("context_size")
    # Loop though the files within the input folder.

    collated_output = []
    for foldername, dirs, filenames in os.walk(input_folder):
        for filename in filenames:
            # Check if pdf file
            if not filename.endswith(".pdf"):
                continue
            # PDF File found
            inp_pdf_file = os.path.join(foldername, filename)
            print("Processing file =", inp_pdf_file, kwargs.get("context_size"))
            output = process_file(
                input_file=inp_pdf_file,
                output_file=None,
                search_str=search_str,
                action=action,
                pages=pages,
                color=color,
                context_size=context_size,
            )

            if action == "Extract Context":
                # print(output)
                collated_output.append(output)
        if not recursive:
            break
    return collated_output


def is_valid_path(path):
    """
    Validates the path inputted and checks whether it is a file path or a folder path
    """
    if not path:
        raise ValueError("Invalid Path")
    if os.path.isfile(path):
        return path
    elif os.path.isdir(path):
        return path
    else:
        raise ValueError(f"Invalid Path {path}")


def parse_args():
    """
    Get user command line parameters
    """
    parser = argparse.ArgumentParser(description="Available Options")
    parser.add_argument(
        "-i",
        "--input_path",
        dest="input_path",
        type=is_valid_path,
        required=True,
        help="Enter the path of the file or the folder to process",
    )
    parser.add_argument(
        "-a",
        "--action",
        dest="action",
        choices=[
            "Redact",
            "Frame",
            "Highlight",
            "Squiggly",
            "Underline",
            "Strikeout",
            "FreeText",
            "Remove",
        ],
        type=str,
        default="Highlight",
        help="Choose whether to Redact or to Frame or to Highlight or to Squiggly or to Underline or to Strikeout or to Remove",
    )
    parser.add_argument(
        "-p",
        "--pages",
        dest="pages",
        type=tuple,
        help="Enter the pages to consider e.g.: [2,4]",
    )
    action = parser.parse_known_args()[0].action
    if action != "Remove":
        parser.add_argument(
            "-s",
            "--search_str",
            dest="search_str",  # lambda x: os.path.has_valid_dir_syntax(x)
            type=str,
            required=True,
            help="Enter a valid search string",
        )

        parser.add_argument(
            "-c",
            "--color",
            dest="color",  # lambda x: os.path.has_valid_dir_syntax(x)
            type=str,
            required=True,
            help="Enter a valid color",
        )

    path = parser.parse_known_args()[0].input_path
    if os.path.isfile(path):
        parser.add_argument(
            "-o",
            "--output_file",
            dest="output_file",
            type=str,  # lambda x: os.path.has_valid_dir_syntax(x)
            help="Enter a valid output file",
        )
    if os.path.isdir(path):
        parser.add_argument(
            "-r",
            "--recursive",
            dest="recursive",
            default=False,
            type=lambda x: (str(x).lower() in ["true", "1", "yes"]),
            help="Process Recursively or Non-Recursively",
        )
    args = vars(parser.parse_args())
    # To Display The Command Line Arguments
    print("## Command Arguments #################################################")
    print("\n".join("{}:{}".format(i, j) for i, j in args.items()))
    print("######################################################################")
    return args


def edit_pdfs(args):
    # If File Path
    if os.path.isfile(args.get("input_path")):
        # Extracting File Info
        extract_info(input_file=args.get("input_path"))
        # Process a file
        output = process_file(
            input_file=args.get("input_path"),
            output_file=args.get("output_file"),
            search_str=args.get("search_str")
            if "search_str" in (args.keys())
            else None,
            color=args.get("color") if "color" in (args.keys()) else "yellow",
            pages=args.get("pages"),
            action=args.get("action"),
            context_size=args.get("context_size"),
        )
        output = [output]
    # If Folder Path
    elif os.path.isdir(args.get("input_path")):
        # Process a folder
        output = process_folder(
            input_folder=args.get("input_path"),
            search_str=args.get("search_str")
            if "search_str" in (args.keys())
            else None,
            color=args.get("color") if "color" in (args.keys()) else "yellow",
            action=args.get("action"),
            pages=args.get("pages"),
            recursive=args.get("recursive"),
            context_size=args.get("context_size"),
        )
    if args.get("action") == "Extract Context":
        # Piece together the extracted output for all files

        # write the output to file
        # first convert to a pandas dataframe
        # then write to csv

        columns = ["filename", "search_str", "page", "excerpt"]

        output_dict = [
            {
                "filename": result["filename"],
                "search_str": args.get("search_str"),
                "page": page_num,
                "excerpt": excerpt,
            }
            for result in output
            for page_num, excerpt in result.get("hits")
        ]

        # print(output)
        df = pd.DataFrame(output_dict, columns=columns)

        # Make the search result be based on the search string and input path
        output_name = (
            "search_context_"
            + args.get("search_str")
            + "_"
            + args.get("input_path").split("/")[-1]
            + ".csv"
        )

        df.to_csv(output_name, index=False)

        return output


if __name__ == "__main__":
    # Parsing command line arguments entered by user
    args = parse_args()
    # If File Path
    if os.path.isfile(args.get("input_path")):
        # Extracting File Info
        extract_info(input_file=args.get("input_path"))
        # Process a file
        process_file(
            input_file=args.get("input_path"),
            output_file=args.get("output_file"),
            search_str=args.get("search_str")
            if "search_str" in (args.keys())
            else None,
            color=args.get("color") if "color" in (args.keys()) else "yellow",
            pages=args.get("pages"),
            action=args.get("action"),
        )
    # If Folder Path
    elif os.path.isdir(args.get("input_path")):
        # Process a folder
        process_folder(
            input_folder=args.get("input_path"),
            search_str=args.get("search_str")
            if "search_str" in (args.keys())
            else None,
            color=args.get("color") if "color" in (args.keys()) else "yellow",
            action=args.get("action"),
            pages=args.get("pages"),
            recursive=args.get("recursive"),
        )
