import os

file_path = r'C:\OLIA-TEAM\src\lib\components\layout\Sidebar.svelte'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

insert_idx = -1
for i, line in enumerate(lines):
    if 'const initChannels = async () => {' in line:
        insert_idx = i
        break

if insert_idx != -1:
    new_method = """\tconst handleChannelSubmit = async (channel) => {
\t\tconst res = await createNewChannel(localStorage.token, channel).catch((error) => {
\t\t\ttoast.error(error);
\t\t\treturn null;
\t\t});

\t\tif (res) {
\t\t\tawait initChannels();
\t\t\tshowCreateChannel = false;
\t\t}
\t};

"""
    lines.insert(insert_idx, new_method)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully patched Sidebar.svelte")
else:
    print("Could not find initChannels in Sidebar.svelte")
