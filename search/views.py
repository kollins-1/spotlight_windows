import os
from django.shortcuts import render
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from .forms import SearchForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from urllib.parse import unquote  # To decode the URL-encoded file path

def search_files(request):
    query = request.GET.get('query', '')
    results = []
    index_dir = "search_index"  # The directory where the Whoosh index is stored

    if query:
        try:
            ix = open_dir(index_dir)  # Open the Whoosh index directory
            with ix.searcher() as searcher:
                parser = QueryParser("title", ix.schema)
                search_query = parser.parse(query)
                search_results = searcher.search(search_query)

                # Collect results in a list to pass to the template
                results = [{'title': hit['title'], 'path': hit['path']} for hit in search_results]

        except Exception as e:
            # Log the error or print for debugging
            print("Error accessing the index:", e)

    form = SearchForm(initial={'query': query})
    return render(request, 'search/search_results.html', {'form': form, 'results': results})

def open_file(request, file_path):
    try:
        # Decode the file path from URL encoding
        decoded_file_path = unquote(file_path)

        # Use os.startfile to open the file with its default application
        os.startfile(decoded_file_path)
    except Exception as e:
        # If there is an error (e.g., file not found), handle it
        print(f"Error opening file: {e}")
    return HttpResponseRedirect(reverse('search_files'))  # Redirect back to search results
