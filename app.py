import os
import time

import streamlit as st
from fitz.utils import getColorList

from pdf_highlighter import edit_pdfs

cl = getColorList()
colors = [
    "yellow",
    "green",
    "pink",
    "cyan",
    "orange",
    "plum",
    "red",
    "wheat",
    "olive",
    "gold",
    "purple",
    "brown",
    "magenta",
    "beige",
    "blue",
    "lavender",
    "chartreuse",
]


def baloon_animation():
    progress_bar = st.progress(0)
    status_text = st.empty()
    lines = list(range(1, 101))
    chart = st.line_chart(lines)

    for i in range(100):
        # Update progress bar.
        progress_bar.progress(i + 1)

        lines = lines[1:] + lines[:1]

        # Update status text.
        status_text.text("The latest random number is: %s" % lines[0])

        # Append data to the chart.
        chart.add_rows(lines)

        # Pretend we're doing some computation that takes time.
        time.sleep(0.1)
    status_text.text("Done!")
    st.balloons()


def get_pdf_files():
    pdfs_and_dirs = [
        file for file in os.listdir() if file.endswith(".pdf") or os.path.isdir(file)
    ]

    # Filter out hidden files and folders
    pdfs_and_dirs = [
        item for item in pdfs_and_dirs if (item[0] != ".") and (item[0] != "_")
    ]

    # Sort the list by whether the file ends with .pdf, then alphabetically
    pdfs_and_dirs.sort(key=lambda x: (x[-4:] != ".pdf", x))
    return pdfs_and_dirs


def data_input():
    pdfs_and_dirs = get_pdf_files()

    path = st.selectbox("Select the file or folder to view", pdfs_and_dirs)
    overwrite = st.checkbox(
        "Check to overwrite the original file/s. \nOverwrites by default on folders.",
        value=True,
    )

    output_file = None
    if overwrite is False:
        output_file = st.text_input("Enter the name of the output file")

    return {"path": path, "overwrite": overwrite, "output_file": output_file}


def select_action():
    # Get the function to apply to the file or folder
    action = st.selectbox(
        "Select the function to apply to the file or folder",
        [
            "Highlight",
            "Redact",
            "Underline",
            "Strikeout",
            "Extract Context",
            "Remove",
            # "FreeText",
            # "MultiHighlight",
            # "Frame",
            # "Squiggly",
        ],
    )
    return action


def extract_search_terms():
    col1, col2 = st.columns(2)
    search_strings = []
    uploaded_file = col2.file_uploader("Upload text file containing search terms.")
    if uploaded_file:
        for line in uploaded_file:
            line = line.decode("utf-8").rstrip("\r\n")

            search_strings.append(line)

        for i, search_str in enumerate(search_strings):
            col2.write(f"Search term {i+1}: {search_str}")

    else:
        num_strings = col1.number_input(
            "Enter the number of search terms", min_value=1, max_value=50, value=3
        )

        for i in range(num_strings):
            search_strings.append(
                col1.text_input(f"Enter search term {i+1}", key="search_" + str(i))
            )
    return search_strings


def search_parameters_input(action):
    search_strings = [None]

    context_size = None
    if action != "Remove":
        search_strings = extract_search_terms()

        if action == "Extract Context":
            context_size = str(
                st.number_input(
                    "Enter the context size (roughly how many lines to extract)",
                    min_value=1,
                    max_value=20,
                    value=5,
                )
            )

    return {"search_strings": search_strings, "context_size": context_size}


def run(search_strings, context_size, action, path, output_file):
    try:
        outputs = []
        for i, search_str in enumerate(search_strings):
            if search_str == "":
                continue
            output = edit_pdfs(
                {
                    "input_path": path,
                    "action": action,
                    "color": colors[i % len(colors)],
                    "search_str": search_str,
                    "pages": None,
                    "output_file": output_file,
                    "recursive": True,
                    "context_size": context_size,
                }
            )
            outputs.append(output)

            if action == "Extract Context":
                st.write("Extracted context:")
                st.write(output)

    except PermissionError:
        st.write(
            "PermissionError: "
            // +"Please close the pdf file/s you are trying to edit."
        )
    except Exception as e:
        st.write(e)


def main():
    st.title("Sweet Dee Dee's PDF Editor")

    # Get the file or folder to edit
    data = data_input()

    action = select_action()

    # Get the search terms
    search_params = search_parameters_input(action)

    # click button to run the edit_pdfs function with the arguments above
    if st.button("Run"):
        run(
            search_params["search_strings"],
            search_params["context_size"],
            action,
            data["path"],
            data["output_file"],
        )

        # Display a message to the user that the function has been applied
        # Provide a download link or link to the file in the output folder
        st.write("Done! I love you!")


if __name__ == "__main__":
    main()

# To run the app, run the following command in the terminal:
# streamlit run app.py
# Things to do
# """
# upload files
# download files
# detect whether pdf is searchable (e.g. not just scanned image pdf)#
#
# if you can highligh all keywords
# then someone has to still go through and review keywords
# and then do xyz
# better would be if it could capture the context of the keyword
# and export the context to a csv file
# so that the user can review the context
#
# e.g. if one of the keywords was "token" then that would be the term
# and rows would be hits (context/clause) for that term in a pdf
# and columns would be corresponding to different pdfs
#
# semantic search mode
#
#
# """
