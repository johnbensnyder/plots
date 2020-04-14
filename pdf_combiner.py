from pathlib import Path
import pandas as pd
from collections import defaultdict
import PyPDF2
import argparse

class PDF_Combiner(object):
    """
    The PDF combiner is a tool to group together PDF files for research
    proposals based on a the lead research ID number and all associated
    research proposal ID numbers. For example, if researcher Cleetus Spuckler
    has lead ID 12345 and proposals 7845, 9832, and 0714 in pdf files
    12345.pdf, 12345_coa.pdf, 7845.pdf, 9832.pdf, 9832_coa.pdf, and 0714.pdf,
    this tool will combine all this files in the same order listed above, and
    output a new file with the name Spuckler_12345_combined.pdf
    """
    def __init__(self, spreadsheet, src_dir):
        """
        Parameters
        ----------
        
        spreadsheet_filename : str
            The csv file containing proposal and lead author information
            Should have columns "Lead" "Proposal" and "PI NAME"
        src_dir : str
            The file path to the directory containing the pdf files
            associated with the proposals in the spreadsheet
            
        """
        self.spreadsheet = spreadsheet
        self.src_dir = Path(src_dir)
        self.proposal_groups, self.names = self.create_dictionaries()
        
    def create_dictionaries(self):
        """
        We need two sets of dictionaries for building the files.
        
        The first contains the lead proposal as the key, and a 
        list of all associated proposals. The first item in the 
        list should be the lead proposal itself.
        
        Second, we need a dictionary of author last names, where
        the key is again the lead proposal ID number, and the
        values are the author last names.
        
        Parameters
        ----------
        
        None
        
        Returns
        -------
        
        proposal_groups : dict
            A dictionary of proposal IDs grouped by lead ID as key
        
        names : dict
            A dictionary of author names with lead ID as key
        """
        proposals = pd.read_csv(self.spreadsheet)
        # check for na values in lead id
        proposals['Lead'] = proposals['Lead'].fillna(proposals['Proposal']).astype(int)
        proposal_groups = defaultdict(list)
        for lead, proposal in zip(proposals['Lead'], proposals['Proposal']):
            proposal_groups[lead].append(proposal)
        # make sure lead proposal is first in the list
        proposal_groups = {i:sorted(j, key=lambda x: 1 if x==i else 2) \
                           for i,j in proposal_groups.items()}
        # make an associated dictionary of names
        names = {i: proposals.loc[(numbers['Lead']==i) & \
                                  (proposals['Lead']==proposals['Proposal'])] \
                                  ['PI NAME'].values[0].split(',')[0] \
                                  for i in proposal_groups.keys()}
        return proposal_groups, names
    
    def pdf_file_getter(self, a_dict_key):
        """
        For a given lead proposal ID, get all associated files in the src_dir
        We want to make sure the first file is the lead ID alone (12345.pdf, not 12345_coa.pdf)
        to do this, sort each set of files by length of the filename.
        
        Parameters
        ----------
        
        a_dict_key : int
            A lead proposal ID number
            
        Returns
        -------
        
        files : list
            A list of filenames for all PDFs associated with the lead proposal ID
            
        """
        files = []
        for proposal in self.proposal_groups[a_dict_key]:
            files_for_id = [i.as_posix() for i in \
                            self.src_dir.glob('{}*.pdf'.format(proposal))]
            files_for_id = sorted(files_for_id, key=len)
            files.extend(files_for_id)
        return files
    
    def pdf_combiner(self, pdf_list):
        """
        Once we have a list of files, we want to combine them all into a single PDF
        
        Parameters
        ----------
        
        pdf_list : list
            A list of all pdf files to combine
        
        Returns
        -------
        
        pdfWriter : PyPDF2.PdfFileWriter
            A pdf file writer object
        
        """
        pdfs = [PyPDF2.PdfFileReader(i) for i in pdf_list]
        pdfWriter = PyPDF2.PdfFileWriter()
        for pdf in pdfs:
            for pagenum in range(pdf.numPages):
                page = pdf.getPage(pagenum)
                pdfWriter.addPage(page)
        return pdfWriter
    
    def dump_pdf(self, pdf_object, file_name):
        """
        Dumps the contents of a pdf file writer to
        a file
        
        Parameters
        ----------
        
        pdf_object : PyPDF2.PdfFileWriter
            A pdf file writer object, the output of pdf_combiner
            
        file_name : str
            The name of the file to write
        
        Returns
        -------
        
        None
        
        """
        with open(file_name, 'wb') as outfile:
            pdf_object.write(outfile)
        
    def create_files(self, out_dir=None):
        """
        Creates all new PDF files at once
        
        Parameters
        ----------
        
        out_dir : str (optional)
            The output directory to write files to
            If not specified, will output to the src_dir
        
        Returns
        -------
        
        None
        
        """
        if out_dir:
            out_dir = Path(out_dir)
            out_dir.mkdir(exists_ok=True)
        else:
            out_dir = self.src_dir
        for num in self.proposal_groups.keys():
            try:
                file_list = self.pdf_file_getter(num)
                pdf_object = self.pdf_combiner(file_list)
                file_name = out_dir.joinpath("{0}_{1}_combined.pdf". \
                                             format(self.names[num], num)).as_posix()
                pdf_writer(pdf_object, file_name)
            except:
                print("error in writing {0} pdf file".format(num))
            
def parse_args():
    cmdline = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    cmdline.add_argument('spreadsheet', type=str,
                         help="""Path to the csv file containing the
                                 proposal information""")
    cmdline.add_argument('src_dir', type=str,
                         help="""Path to the dir containing the pdf files""")
    cmdline.add_argument('--out_dir', type=str, default=None,
                         help="""Output path for the new combined files""")
    return cmdline
    
def main(spreadsheet, src_dir, out_dir):
    file_combiner = PDF_Combiner(spreadsheet, src_dir)
    file_combiner.create_files(out_dir)

if __name__=='__main__':
    cmdline = add_cli_args()
    FLAGS, unknown_args = cmdline.parse_known_args()
    main(FLAGS.spreadsheet, FLAGS.src_dir, FLAGS.out_dir)
