def inject_css():
    import site
    import os

    css = '''.ag-root,
    .ag-root-wrapper,
    .ag-ltr .ag-cell {
        border: none;
    }

    .ag-root-wrapper {
        border-top: 2px solid #000000;
    }

    .ag-root * {
        font-family: Helvetica, arial, sans-serif;
    }

    .ag-row,
    .ag-header-row {
        border-bottom: 1px solid #000;
        background-color: #ffffff;
        color: #000000;
    }

    .ag-row-hover::before {
        background-color: #efefef !important;
    }

    .ag-header-cell,
    .ag-header-group-cell-label {
        color: #000000;
    }'''
    try:
        site_packages_dir = ''
        for dir_ in site.getsitepackages():
            if 'site-packages' in dir_:
                site_packages_dir = dir_

        st_aggrid_abs_path = ''
        for root, dirs, files in os.walk(site_packages_dir, topdown=False):
            for name in dirs:
                if 'st_aggrid' in name:
                    st_aggrid_abs_path = os.path.join(root, name)

        css_file_dir = os.path.join(st_aggrid_abs_path,
                                    'frontend',
                                    'build',
                                    'static',
                                    'css')

        css_files = []
        for file in os.listdir(css_file_dir):
            if file.endswith('.css'):
                css_files.append(os.path.join(css_file_dir, file))

        for file in css_files:
            content = ''
            with open(file, 'r') as f:
                content = f.read()
            if css not in content:
                with open(file, 'a') as f:
                    f.write(css)
    except:
        print('Hi something wrong with Ag-grid css injection')