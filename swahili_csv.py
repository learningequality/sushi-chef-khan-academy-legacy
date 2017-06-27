import pickle
import csv


with open('node_data_en.pickle', 'rb') as handle:
    en_data = pickle.load(handle)

with open('node_data_sw.pickle', 'rb') as handle:
    sw_data = pickle.load(handle)

spread = en_data
for sw in sw_data:
    if 'khan/math' in sw.get('path'):
        if sw.get('kind') == 'Video':
            for idx in range(len(spread)):
                if 'khan/math' in spread[idx].get('path'):
                    if spread[idx].get('kind') == 'Video':
                        if spread[idx].get('id') == sw.get('id'):
                            if sw.get('translated_youtube_lang') == 'sw':
                                spread[idx] = sw


with open('swahili_spreadsheet.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    data = [['TITLE', 'LICENSE', 'DOMAIN', 'SUBJECT', 'TOPIC', 'TUTORIAL', 'TITLE ID', 'FORMAT', 'DUBBED?', 'ENGLISH', 'KISWAHILI']]
    csvwriter.writerows(data)
    
    for node in spread:
        if 'khan/math' in node.get('path'):
            row = []
            subject = node.get('path').split('/')[2]
            if node.get('kind') == 'Video':
                if node.get('translated_youtube_lang') == 'sw':
                    row.append(node.get('title'))  # title
                    row.append(node.get('license_name').split('(')[0])  # license
                    row.append('Math')  # domain
                    row.append(subject)  # subject
                    row.append(node.get('path').split('/')[3])  # topic
                    row.append(node.get('path').split('/')[4].replace('cc-', '').replace(subject + '-', ''))  # tutorial
                    row.append(node.get('slug'))  # slug/title ID
                    row.append('Video')  # format
                    row.append('YES')  # dubbed
                    row.append(node.get('id').split('=')[-1])  # english youtube_id
                    row.append(node.get('youtube_id'))  # dubbed youtube_id
                else:
                    row.append(node.get('title'))  # title
                    row.append(node.get('license_name').split('(')[0])  # license
                    row.append('Math')  # domain
                    row.append(subject)  # subject
                    row.append(node.get('path').split('/')[3])  # topic
                    row.append(node.get('path').split('/')[4].replace('cc-', '').replace(subject + '-', ''))  # tutorial
                    row.append(node.get('slug'))  # slug/title ID
                    row.append('Video')  # format
                    row.append('NO')  # dubbed
                    row.append(node.get('id'))  # english youtube_id
                    row.append('')  # dubbed youtube_id
                csvwriter.writerows([row])
            elif node.get('kind') == 'Exercise':
                row.append(node.get('title'))  # title
                row.append('')  # license
                row.append('Math')  # domain
                row.append(node.get('path').split('/')[2])  # subject
                row.append(node.get('path').split('/')[3])  # topic
                row.append(node.get('path').split('/')[4].replace('cc-', '').replace(subject + '-', ''))  # tutorial
                row.append(node.get('slug'))  # slug/title ID
                row.append('Exercise')  # format
                row.append('')  # dubbed
                row.append('')  # english youtube_id
                row.append('')  # dubbed youtube_id
                csvwriter.writerows([row])

