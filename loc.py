import os
from collections import defaultdict

def count_lines_in_file(file_path):
    total_lines = 0
    code_lines = 0
    comment_lines = 0
    blank_lines = 0
    in_multiline_comment = False

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            if in_multiline_comment:
                comment_lines += 1
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    in_multiline_comment = False
                continue

            if stripped.startswith('"""') or stripped.startswith("'''"):
                comment_lines += 1
                if not (stripped.endswith('"""') and len(stripped) > 3) and not (stripped.endswith("'''") and len(stripped) > 3):
                    in_multiline_comment = True
                continue

            if stripped.startswith('#'):
                comment_lines += 1
            else:
                code_lines += 1

    return total_lines, code_lines, comment_lines, blank_lines

def count_lines_by_directory(directory):
    dir_totals = {}

    for root, dirs, files in os.walk(directory):
        total = code = comments = blanks = 0
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                t, c, cm, b = count_lines_in_file(file_path)
                total += t
                code += c
                comments += cm
                blanks += b
        # Only add directories that have files directly
        if total > 0:
            dir_totals[root] = {'total': total, 'code': code, 'comments': comments, 'blanks': blanks}

    # Print results
    print("\nLines of code by directory:\n")
    for dir_path, counts in sorted(dir_totals.items()):
        print(f"{dir_path}: total={counts['total']}, code={counts['code']}, comments={counts['comments']}, blanks={counts['blanks']}")

    # Overall totals
    overall = {'total': 0, 'code': 0, 'comments': 0, 'blanks': 0}
    for counts in dir_totals.values():
        for k in overall:
            overall[k] += counts[k]

    print("\nOverall Totals:")
    print(f"Total lines: {overall['total']}")
    print(f"Code lines: {overall['code']}")
    print(f"Comment lines: {overall['comments']}")
    print(f"Blank lines: {overall['blanks']}")


if __name__ == "__main__":
    folder = input("Enter directory path to scan: ")
    count_lines_by_directory(folder)
