# streamlit_app.py
import streamlit as st
import pandas as pd
import os

# --- Core Functions from your existing MTM Validator ---

def validate_against_spec(df_test, product_spec_df, filename):
    errors = []

    # Merge on 'NO' and 'ITEM'
    for _, row in df_test.iterrows():
        test_no = str(row['NO']).strip()
        test_item = str(row['ITEM']).strip()

        spec_match = product_spec_df[
            (product_spec_df['NO'].astype(str).str.strip() == test_no) |
            (product_spec_df['ITEM'].astype(str).str.strip().str.upper() == test_item.upper())
        ]

        if spec_match.empty:
            errors.append(f"{filename}: Test NO {test_no} ({test_item}) not found in spec.")
            continue

        spec_row = spec_match.iloc[0]

        def compare_field(field, val_test, val_spec):
            if pd.isna(val_spec) or val_spec == "":
                return True  # Nothing to check
            try:
                return float(val_test) == float(val_spec)
            except:
                return False

        # Check Min, Max, Bias1-3
        checks = [
            ('Min', row['Min'], spec_row.get('Min')),
            ('Max', row['Max'], spec_row.get('Max')),
            ('Bias1', row['Bias1'], spec_row.get('Bias1')),
            ('Bias2', row['Bias2'], spec_row.get('Bias2')),
            ('Bias3', row['Bias3'], spec_row.get('Bias3')),
        ]

        for field, val_test, val_spec in checks:
            if not compare_field(field, val_test, val_spec):
                errors.append(
                    f"{filename}: Test NO {test_no} ({test_item}) {field} mismatch. MTM: {val_test} ≠ Spec: {val_spec}"
                )

    return errors

def parse_sort_line_dynamic(line):
    try:
        if '^' in line:
            prefix, item = line.split('^', 1)
            item = item.strip()
        else:
            prefix = line.strip()
            item = ""

        multi_word_tokens = {
            'ALL PASS': 'ALL_PASS',
            'BIN OUT': 'BIN_OUT',
            'BIN IN': 'BIN_IN',
        }
        for full, token in multi_word_tokens.items():
            prefix = prefix.replace(full, token)

        tokens = prefix.strip().split()
        tokens = [
            token.replace('_', ' ') if token in multi_word_tokens.values() else token
            for token in tokens
        ]

        if len(tokens) < 3:
            return []

        bin_no = tokens[0]
        result = tokens[1]
        logic = tokens[2]
        codes = tokens[3:]

        return [bin_no, result, logic] + codes + [item]

    except Exception as e:
        return []


def validate_sort_plan(bin_lines, required_bin=None, check_pass_format=False, check_single_pass=False, check_bin_out=False, check_osc=False):
    errors = []
    pass_lines = []
    bin_usage = {}
    has_bin_out = False
    has_osc = False

    for filename, line in bin_lines:
        parsed = parse_sort_line_dynamic(line)
        if not parsed:
            continue

        bin_no = parsed[0].strip()
        result = parsed[1].strip().upper()
        logic = parsed[2].strip().upper()
        codes = parsed[3:-1]
        code_0 = codes[0].strip().upper() if codes else ""

        bin_usage.setdefault(bin_no, []).append((filename, line))

        if check_pass_format and result == "PASS":
            if logic != "AND" or code_0 != "ALL PASS" or bin_no != required_bin:
                errors.append(
                    f"{filename}: Invalid PASS bin (BIN={bin_no}). Expected BIN={required_bin}, Logic='AND', Code_0='ALL PASS'."
                )

        if result == "PASS":
            pass_lines.append((filename, bin_no, line))

        if check_bin_out:
            if any(code.upper() == "BIN OUT" for code in codes):
                has_bin_out = True

        if check_osc:
            if any(code.upper() == "OSC" for code in codes):
                has_osc = True

    if check_single_pass:
        if len(pass_lines) > 1:
            errors.append(
                f"❌ Multiple PASS bins found ({len(pass_lines)}). Expected only one:\n" +
                "\n".join([f"{f}: {l}" for f, _, l in pass_lines])
            )

    if check_bin_out and not has_bin_out:
        errors.append("❌ Sort Plan does not contain 'BIN OUT' in any code column.")

    if check_osc and not has_osc:
        errors.append("❌ Sort Plan does not contain 'OSC' in any code column.")

    return errors


def validate_test_plan(df, filename, settings):
    errors = []
    df['Sort'] = df['Sort'].replace({'1': 'FAIL', '2': 'PASS', '3': ''})
    df['Condition_Sort'] = df['Condition_Sort'].replace({'0': '', '1': 'F-T', '2': 'P-T', '3': 'P/F-T'})
    df['AR'] = df['AR'].replace({'1': 'AR', '0': ''})

    if settings["check_branch_fail"]:
        filtered_df = df[df['NO'] != 'MT2000 TEST PROGRAM']
        non_fail_rows = filtered_df[filtered_df['Sort'] != 'FAIL']
        if not non_fail_rows.empty:
            errors.append(f"{filename}: {len(non_fail_rows)} test(s) found where Sort ≠ 'FAIL'.")

    if settings["check_hfe_ar"]:
        for _, row in df.iterrows():
            if str(row['ITEM']).strip().upper() == "HFE" and row['AR'] != "AR":
                errors.append(f"{filename}: HFE test NO {row['NO']} does not use AR option.")

    return errors


def check_sort_coverage(df, bin_rows, filename):
    errors = []
    test_codes = set()
    for no in df['NO'].dropna():
        try:
            num = int(str(no).strip())
            code = f"F{num:03d}"
            test_codes.add(code)
        except ValueError:
            continue

    sort_codes = set()
    for _, line in bin_rows:
        parsed = parse_sort_line_dynamic(line)
        if parsed:
            codes = parsed[3:-1]
            for c in codes:
                if c.startswith('F') and c[1:].isdigit():
                    sort_codes.add(c)

    missing = test_codes - sort_codes
    if missing:
        errors.append(f"{filename}: Missing sort plan coverage for codes: {', '.join(sorted(missing))}")
    return errors


# --- Paper Spec & Mapping management functions ---

def load_mapping(file_path='paper_specs/mtm_product_map.csv'):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        return pd.DataFrame(columns=['Filename', 'Product'])


def save_mapping(df_map, file_path='paper_specs/mtm_product_map.csv'):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df_map.to_csv(file_path, index=False)


def load_spec(product_filename):
    path = os.path.join('paper_specs', product_filename)
    if os.path.exists(path):
        df = pd.read_csv(path)
        
        # Ensure all expected columns are present
        required_cols = [
            'NO', 'ITEM', 'Min', 'Min_Unit', 'Max', 'Max_Unit',
            'Bias1', 'Bias1_Unit', 'Bias2', 'Bias2_Unit',
            'Bias3', 'Bias3_Unit',
            'Compare_Limit', 'Compare_Bias1', 'Compare_Bias2', 'Compare_Bias3'
        ]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""  # or False/None as appropriate

        return df
    else:
        # Return empty DataFrame with full structure
        return pd.DataFrame(columns=required_cols)


def save_spec(df_spec, product_filename):
    os.makedirs('paper_specs', exist_ok=True)
    path = os.path.join('paper_specs', product_filename)

    # Ensure Compare_Limit and Compare_Bias exist
    for col in ['Compare_Limit', 'Compare_Bias']:
        if col not in df_spec.columns:
            df_spec[col] = True  # default

    df_spec.to_csv(path, index=False)



# --- Streamlit App ---

st.set_page_config(page_title="MTM Validator & Paper Spec Editor", layout="wide")

tabs = st.tabs(["MTM Validator", "Paper Spec & Mapping Editor"])

with tabs[0]:
    st.title("📁 MTM File Processor & Validator")

    # Validation Options
    st.sidebar.header("Validation Settings")
    settings = {
        "check_branch_fail": st.sidebar.checkbox("Branch must be FAIL"),
        "check_hfe_ar": st.sidebar.checkbox('HFE must use "AR"'),
        "check_pass_format": st.sidebar.checkbox("Validate PASS bin logic"),
        "check_single_pass": st.sidebar.checkbox("Only one PASS result in sort plan"),
        "check_coverage": st.sidebar.checkbox("Test code coverage in sort plan"),
        "check_bin_out": st.sidebar.checkbox("BIN OUT must be included"),
        "check_osc": st.sidebar.checkbox("OSC must be included"),
        "check_spec_limits": st.sidebar.checkbox("Validate test limits against paper spec"),
    }

    required_bin = st.sidebar.text_input("PASS bin must be BIN =", "11").zfill(2) if settings["check_pass_format"] else None

    uploaded_files = st.file_uploader("Upload .mtm file(s)", type="mtm", accept_multiple_files=True)

    if uploaded_files:
        all_test_rows = []
        all_bin_rows = []
        all_errors = []

        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            test_rows = []
            bin_rows = []
            is_bin = False

            content = uploaded_file.read().decode("latin-1").splitlines()

            for line in content:
                line = line.strip()
                if line == "= TEST BIN DATA =":
                    is_bin = True
                    continue
                elif line == "= END DC BIN DATA =":
                    is_bin = False
                    continue
                elif line.startswith("=") or not line:
                    continue

                if is_bin:
                    bin_rows.append((filename, line))
                else:
                    fields = [f.strip() for f in line.split('^')]
                    fields.insert(0, filename)
                    test_rows.append(fields)

            if not test_rows:
                all_errors.append(f"{filename}: No test data found.")
                continue

            # Convert test_rows to DataFrame
            df = pd.DataFrame(test_rows)
            columns = [
                'Filename', 'NO', 'ITEM', 'Unknown_3', 'Code', 'Min', 'Min_Unit', 'Max',
                'Max_Unit', 'Sort', 'Condition_Sort', 'Unknown_11', 'Bias1', 'Bias1_Unit',
                'Bias2', 'Bias2_Unit', 'Bias3', 'Bias3_Unit', 'Test_Time', 'Test_Time_Unit',
                'RV', 'Unknown_21', 'CP', 'AR', 'SKIP', 'BVR', 'VP', 'INT'
            ]
            while len(columns) < df.shape[1]:
                columns.append(f"Unknown_{len(columns)}")
            df.columns = columns

            # Run test plan validation
            all_test_rows.extend(df.values.tolist())
            all_bin_rows.extend(bin_rows)
            test_errors = validate_test_plan(df, filename, settings)
            all_errors.extend(test_errors)

            if settings["check_coverage"]:
                coverage_errors = check_sort_coverage(df, bin_rows, filename)
                all_errors.extend(coverage_errors)

        # Sort plan validations
        sort_errors = validate_sort_plan(
            all_bin_rows,
            required_bin=required_bin,
            check_pass_format=settings["check_pass_format"],
            check_single_pass=settings["check_single_pass"],
            check_bin_out=settings["check_bin_out"],
            check_osc=settings["check_osc"]
        )
        all_errors.extend(sort_errors)

        # --- Output Section ---
        st.subheader("✅ Validation Results")

        if all_errors:
            for err in all_errors:
                st.error(err)
        else:
            st.success("All files validated successfully!")

        # Show Test Plan Table
        if all_test_rows:
            df_test = pd.DataFrame(all_test_rows, columns=columns[:len(all_test_rows[0])])
            st.subheader("📊 Aggregated Test Plan")
            st.dataframe(df_test, use_container_width=True)

            # CSV export
            csv_test = df_test.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Test Plan CSV", data=csv_test, file_name="test_plan.csv", mime="text/csv")

        # Show Sort Plan Table
        if all_bin_rows:
            sort_data = []
            max_codes = 0  # To dynamically adjust Code_0, Code_1, ...
        
            for fname, line in all_bin_rows:
                parsed = parse_sort_line_dynamic(line)
                if parsed:
                    sort_data.append([fname] + parsed)
                    max_codes = max(max_codes, len(parsed) - 4)  # Exclude Bin, Result, Logic, Item

            # Build dynamic column names
            base_cols = ['Filename', 'Bin', 'Result', 'Logic']
            code_cols = [f"Code_{i}" for i in range(max_codes)]
            final_cols = base_cols + code_cols + ['Item']

            # Pad rows so they all have same number of columns
            padded_rows = []
            for row in sort_data:
                row_core = row[:4]
                codes = row[4:-1]
                item = row[-1]
                padded_codes = codes + [''] * (max_codes - len(codes))
                padded_rows.append(row_core + padded_codes + [item])

            df_sort = pd.DataFrame(padded_rows, columns=final_cols)

            st.subheader("📋 Aggregated Sort Plan")
            st.dataframe(df_sort, use_container_width=True)

            # CSV export
            csv_sort = df_sort.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Sort Plan CSV", data=csv_sort, file_name="sort_plan.csv", mime="text/csv")

        # Load mapping to get product spec
        map_path = "paper_specs/mtm_product_map.csv"
        mapping_df = load_mapping(map_path)
        mapped_row = mapping_df[mapping_df['Filename'] == filename]

        if settings["check_spec_limits"] and not mapped_row.empty:
            product_file = mapped_row.iloc[0]['Product']
            spec_df = load_spec(product_file)

            limit_errors = validate_against_spec(df, spec_df, filename)
            all_errors.extend(limit_errors)
        elif settings["check_spec_limits"]:
            all_errors.append(f"{filename}: No product mapping found to validate limits.")



with tabs[1]:
    st.title("📄 Paper Spec & Mapping Editor")

    # Load current mapping
    map_path = "paper_specs/mtm_product_map.csv"
    mapping_df = load_mapping(map_path)

    st.subheader("MTM to Product Spec Mapping")

    # Show mapping table editable
    edited_mapping = st.data_editor(mapping_df, num_rows="dynamic", use_container_width=True)

    if st.button("Save Mapping"):
        save_mapping(edited_mapping, map_path)
        st.success("Mapping saved!")

    # Select product to edit paper spec
    products = edited_mapping['Product'].dropna().unique()
    product_selected = st.selectbox("Select Product Spec to Edit", options=products)

    if product_selected:
        spec_df = load_spec(product_selected)

        # Ensure boolean fields are interpreted correctly
        for col in ['Compare_Limit', 'Compare_Bias']:
            if col in spec_df.columns:
                spec_df[col] = spec_df[col].astype(str).str.lower().map({
                    'true': True, 'false': False
                }).fillna(True)

        st.subheader(f"Editing Spec for Product: {product_selected}")

        # Show the editable DataFrame
        edited_spec = st.data_editor(spec_df, num_rows="dynamic", use_container_width=True)


        if st.button("Save Paper Spec"):
            save_spec(edited_spec, product_selected)
            st.success(f"Paper Spec '{product_selected}' saved!")

# End of app
