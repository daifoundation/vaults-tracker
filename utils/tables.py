#  Copyright 2021 DAI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# link generation for html table
def link(item, url, title=None):
    if title:
        title = 'title="%s"' % title
    else:
        title = ''
    return '<a %s href="%s">%s</a>' % (title, url, item)


# simple html table from a list
def html_table(content, widths=None, table_class='simple-table', table_id='sorted-table', tooltip=True):

    if len(content) > 1:
        html = "<table " + ("class='%s'" % table_class if table_class else '') + ("id='%s'" % table_id if table_id else '') + ">"
        html += "<thead><tr>"
        for i, column in enumerate(content[0]):
            if widths and len(widths) > i:
                width = widths[i]
            else:
                width = 'auto'
            html += "<th width='%s'>" % width + str(column) + "</th>"
        html += "</tr></thead>"
        html += "<tbody>"
        for content_row in content[1:]:
            html += "<tr>"
            for i, content_item in enumerate(content_row):
                if tooltip and i == len(content_row) - 1:
                    html += '<td title="%s">' % str(content_item) + str(content_item) + "</td>"
                else:
                    html += "<td>" + str(content_item) + "</td>"
            html += "</tr>"
        html += "</tbody>"
        html += "</table>"
    else:
        html = ''

    return html
