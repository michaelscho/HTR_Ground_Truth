import os
import json
from bs4 import BeautifulSoup
import re

class Collation:

    def __init__(self):
        self.path_to_collations = ""
        self.path_to_json = ""
        self.html_filename = ""
        self.filenames = self.get_files_to_collate()
        self.collatex_path = self.get_collatex_path()
        
        

    def get_collatex_path(self):
        # get location of collatex
        pwd = os.path.dirname(__file__)
        relative_path = "resources"
        path_to_collatex = os.path.abspath(os.path.join(pwd, os.pardir, relative_path, 'collatex-tools-1.7.1.jar'))
        print(path_to_collatex)
        return path_to_collatex


    def get_files_to_collate(self):
        # get location of files to collate
        pwd = os.path.dirname(__file__)
        relative_path_input = "data/Collation/input"
        relative_path_output = "data/Collation/output"
        self.path_to_collations = os.path.join(pwd, os.pardir, relative_path_input)
        self.path_to_json = os.path.join(pwd, os.pardir, relative_path_output, 'collation.json')
        self.html_filename = os.path.join(pwd, os.pardir, relative_path_output, 'collation.html')
        print(self.path_to_collations)
        list_of_files_to_collate = os.listdir(self.path_to_collations)
        for i in range(len(list_of_files_to_collate)):
            list_of_files_to_collate[i] = os.path.join(pwd, os.pardir, relative_path_input, list_of_files_to_collate[i])
        return list_of_files_to_collate

    def collate_witnesses(self):
        #execute = 'java -jar ' + self.collatex_path + ' -f json -o ' + self.path_to_json + " " + ' '.join(self.filenames)
        #print(execute)
        #os.system(execute)        
        self.collation_to_html()
        self.output_html(self.html_filename)
        
    def collation_to_html(self):
        ms_string = ""
        sigla_html = '<html><body><table style="width:96%;"><tbody><tr>'

        for m in os.listdir(self.path_to_collations):
            sigla_html = sigla_html + '<th>' + m + '</th>'
        sigla_html = sigla_html + '</tr>'
        table_html = sigla_html

        with open(self.path_to_json) as json_file:
            data = json.load(json_file)
            #print(data)
        i = 0
        while i < len(data['table']):
            table_html = table_html + '<tr>'
            e = 0
            while e < len(os.listdir(self.path_to_collations)):
                cell = '<td>' + "".join(data['table'][i][e]) + '</td>'
                table_html = table_html + cell
                e += 1
            table_html = table_html + '</tr>'
            i += 1
        table_html = table_html + '</table><script>function isChecked(elem) {elem.parentNode.parentNode.style.backgroundColor = (elem.checked) ? \'white\' : \'red\';}</script></body></html>'
        table_html = table_html.replace('   </td>','</td>')
        table_html = table_html.replace('  </td>','</td>')
        table_html = table_html.replace(' </td>','</td>')

        with open(self.html_filename,'w') as html_output:
            html_output.write(table_html)


    def output_html(self, html_filename):

        with open(html_filename) as f:
            # open collation file in markdown format
            html = f.read()

            soup = BeautifulSoup(html, 'lxml')

            rows = soup.find("table").find("tbody").find_all("tr")
            e = 1
            for row in rows:
                cells = row.find_all("td")
                cells_to_evaluate = []
                for cell in cells:
                    text_cell = cell.get_text()
                    text_cell = re.sub('\s+',' ',text_cell).strip()
                    cells_to_evaluate.append(text_cell)
                print(cells_to_evaluate)
                print(len(set(cells_to_evaluate)))
                if len(set(cells_to_evaluate)) > 1:
                    row['style'] = 'background-color:red;'

                e += 1

            y = 1
            for tr in soup.select('tr'):
                tds = tr.select('td')
                new_td = soup.new_tag('td')
                new_input = soup.new_tag('input', **{'type':'checkbox','id':'termsChkbx', 'onchange':'isChecked(this,\'sub1\')'}) # + '<input type="checkbox" id="termsChkbx" onchange="isChecked(this,\'sub1\')"/>'
                new_td.append(str(y))
                new_td.append(new_input)
                tr.append(new_td)
                y += 1

            with open(html_filename.replace('.html', '_final.html'),'w') as save:
                save.write(str(soup))
    

def main():
        collation = Collation()
        collation.collate_witnesses()

    
if __name__ == "__main__":
    main()