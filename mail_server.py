import socket
from enum import Enum
from database import Database
import sys

class StatusCode(Enum):
    CLOSING=221
    OK=250
    START_MAIL_INPUT=354
    DOMAIN_NOT_AVAILABLE=421 # must close channel
    LOCAL_PROCESSING_ERROR=451
    SYNTAX_ERROR=500
    NOT_IMPLEMENTED=502
    CONNECTION_ESTABLISHED=220
    INVALID_PARAMETER=501
    BAD_SEQUENCE=503
    SERVICE_NOT_AVAILABLE=421
    ADDRESS_UNKNOWN=550

class UnexpectedDisconnection(Exception):
    pass

class SyntaxError(Exception):
    pass

class MailServer:

    def __init__(self, directory, emails, port: int = 65000):

        self.skt = self.create_server(port)

        # domain of sender's email address (everything that comes after '@')
        self.domain = None

        # sender's address
        self.sender = None

        # recipient's address
        self.recipient = None

        self.client_skt = None
        self.client_addr = None

        # call 'add_to_mailbox'
        self.database = Database(directory, emails)

        self.serve_clients()

    def create_server(self, port):

        # create socket with tcp capabitlities (IP and TCP)
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # set additional configuration to the socket. Here we add
        # the capability to reuse the port when the port closes
        # without this we would need to wait for a timeout when the
        # socket closes (sucks for debugging)

        # SOL_SOCKET means the configuration we are setting are
        # protocol independent.
        skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR | socket.SO_REUSEPORT, 1 )

        # bind the socket to a port, so it can listen for connections
        # going for it
        skt.bind(( '', port ))

        # size of unattended connections queue, from this point on the
        # server is working
        skt.listen(5)

        return skt

    def get_client_bytes(self, num_bytes):

        # if zero bytes are recovered, it means that the client disconnected
        buf = self.client_skt.recv(num_bytes).decode("ascii")

        if( len(buf) == 0 ):
            raise UnexpectedDisconnection()
    
        return buf

    def get_command(self):
        
        buf=""
        for i in range(4):
            buf += self.get_client_bytes(1).upper()
            if( buf[-1] == "\n" or buf[-1] == "\r" ):
                raise SyntaxError()
        return buf

    def send_client_bytes(self, buf):

        buf = str(buf)
        # check for no newline
        if( buf[-1] != "\n" ):
            buf = buf + "\r\n"

        return self.client_skt.sendall( buf.encode("ascii") )

    def send_status_code(self, enum_item):
        self.send_client_bytes( str(enum_item.value) + " " + enum_item.name.replace('_', ' ').lower() )

    def is_line_finished(self):

        first_byte = self.get_client_bytes(1)

        if( first_byte == "\n"):
            return True
        elif( first_byte == "\r" ):
            return "\n" == self.get_client_bytes(1)
        else:
            return False

    # return line (without newline) and status code
    def get_line(self, max_bytes=4096):

            buf = self.get_client_bytes(1)
            if( buf[-1] not in ['\r', '\n'] ):
                while( buf[-1] not in ['\r', '\n'] ):
                    if( len(buf) < max_bytes):
                        buf += self.get_client_bytes(1)
                    else:
                        return buf, StatusCode.SYNTAX_ERROR

            # make sure to read last '\n' so we won't read it later
            if( buf[-1] == "\r" and self.get_client_bytes(1) == "\n"):
                return buf[:-1], StatusCode.OK
            elif( buf[-1] == "\n" ):
                return buf[:-1], StatusCode.OK
            else:
                # in this case we got and '\r' NOT followed by and '\n'
                return buf, StatusCode.SYNTAX_ERROR

    def get_new_client(self):
        self.domain = self.recipient = self.sender = None

        if( self.client_skt ):
            self.client_skt.close()
            self.log_disconnection()

        (self.client_skt, self.client_addr) = self.skt.accept()
        if( self.client_skt ):
            # connection established
            self.send_status_code(StatusCode.CONNECTION_ESTABLISHED)

    def log(self, command, line):
        print("'\x1b[32m" + self.client_addr[0] + ":" + str(self.client_addr[1]) + "\x1b[0m' -\n\tcommand: '" + command + "'\n\targs: '" + line + "'\n\tdomain: '" + str(self.domain) + "'\n\tsender: '" + str(self.sender) + "'\n\trecipient: '" + str(self.recipient))

    def log_disconnection(self):
        print('\x1b[31m' + self.client_addr[0] + ":" + str(self.client_addr[1]) + '\x1b[0m')

    def serve_clients(self):

        # accept new client. Since we didn't specify otherwise,
        # the program will hang here until somebody connects
        self.get_new_client()

        # clients can disconnect, but the server never dies
        while(True):

            # get their commands and respond to them...
            # wait for another client if any error occur
            try:
                # 4 first bytes tell us the command given
                command = self.get_command() # NOTE: commands are case insensitive

                # read until the end of the line
                line, status = self.get_line()
                line = line.strip()

                if( status == StatusCode.SYNTAX_ERROR ):
                    self.send_status_code(StatusCode.SYNTAX_ERROR)

                # must be the first command in a session
                if( command == "HELO" ):
                    self.helo(line)
                elif( command == "MAIL"):
                    self.mail(line)
                elif( command == "RCPT" ):
                    self.rcpt(line)
                elif( command == "DATA" ):
                    self.data()
                elif( command == "RSET" ):
                    self.rset()
                elif( command == "NOOP" ):
                    self.noop()
                elif( command == "QUIT" ):
                    self.quit()
                elif( command in ["SEND", "SOML", "SAML", "VRFY", "EXPN", "HELP", "TURN"] ):
                    self.send_status_code(StatusCode.NOT_IMPLEMENTED)
                else:
                    self.send_status_code(StatusCode.SYNTAX_ERROR)

                self.log(command, line)

                if( self.client_skt == None ): self.get_new_client()

            except SyntaxError:
                pass

            except KeyboardInterrupt:
                self.send_client_bytes(StatusCode.SERVICE_NOT_AVAILABLE)
                self.client_skt.close()
                sys.exit()

            except UnexpectedDisconnection:
                self.log_disconnection
                self.get_new_client()

            except Exception as e:
                raise e
                self.get_new_client()

    def helo(self, line):

        # check 'HELO: '
        if not Database.check_domain(line):
            self.send_status_code(StatusCode.INVALID_PARAMETER)
            return

        # RFC says to do so
        self.recipient = None
        self.domain = None

        self.domain = line
        self.send_status_code(StatusCode.OK)

    def mail(self, line):

        # get sender's email address:
        # MAIL FROM: <address>
        # <address> = <1st part of the address>@<domain>

        # check if 'domain' is set
        if( not self.domain ):
            self.send_status_code(StatusCode.BAD_SEQUENCE)
            return

        # RFC says to do so
        self.recipient = None

        # check FROM:
        if( line[:5].upper() != "FROM:" or len(line) <= len("FROM:") ):
            self.send_status_code(StatusCode.SYNTAX_ERROR)
            return

        email = line[6:].strip()

        # check for < and >
        if( email[0] == "<" and email[-1] == ">" ):
            email = email[1:-1]

        # check if email is valid
        if( self.database.check_email_regex(email) and email.split('@')[1] == self.domain):
            self.sender = email
            self.send_status_code(StatusCode.OK)
        else:
            self.send_status_code(StatusCode.INVALID_PARAMETER)
            
    def rcpt(self, line):

        if( not self.sender ):
            self.send_status_code(StatusCode.BAD_SEQUENCE)
            return

        # get recipient's email address
        if( line[:3].upper() != "TO:" or len(line) <= len("TO:")):
            self.send_status_code(StatusCode.SYNTAX_ERROR)
            return

        email = line[3:].strip()

        if( email[0] == "<" and email[-1] == ">"):
            email = email[1:-1]

        # check if email is valid
        if ( self.database.does_email_exist(email) ):

            if( Database.check_email_regex(email) ):
                self.recipient = email
                self.send_status_code(StatusCode.OK)
            else:
                self.send_status_code(StatusCode.INVALID_PARAMETER)
        else:
            self.send_status_code(StatusCode.ADDRESS_UNKNOWN)

    def data(self):
    
        if( not self.recipient ):
            self.send_status_code(StatusCode.BAD_SEQUENCE)
            return

        self.send_status_code(StatusCode.START_MAIL_INPUT)
        data_text = ""

        while(True):
            data_line = self.get_line()[0]
            data_text += data_line + "\n"
            if(data_line == "."):
                self.database.add_to_mailbox(self.recipient,data_text)
                self.send_status_code(StatusCode.OK)
                break
            for character in data_line:
                if(ord(character)>127):
                    self.send_status_code(StatusCode.LOCAL_PROCESSING_ERROR)
                    break

    def rset(self):
        # any info saved about the current email transaction must be discarted.
        # the connection is not finished tough, so don't throw client_skt and
        # client_addr out
        # also, we keep 'self.domain', since this is about the user, not the
        # mail transaction itself
        self.recipient = None
        self.sender = None
        self.domain = None

        self.send_status_code(StatusCode.OK)

    def noop(self):

        self.send_status_code(StatusCode.OK)

    def quit(self):
        # remove current user information
        self.recipient = None
        self.sender = None
        self.domain = None

        # send closing connection signal
        self.send_status_code(StatusCode.CLOSING)

        # close connection (no more receiving/sending) and close socket's file descriptor
        self.client_skt.close()
        self.client_skt = None
        self.client_addr = None

        self.get_new_client()

    def syntax_error(self):
        self.send_status_code(StatusCode.SYNTAX_ERROR)

if( __name__ == "__main__" ):

    if( len(sys.argv) < 2 ):
        print("help: ./mail_server.py <arquivo de emails>")
    else:
        with open(sys.argv[1]) as f:

            emails = [email.strip() for email in f.readlines()]

            for idx, email in enumerate(emails, start=1):
                if( not Database.check_email_regex(email) ):
                    print("Email inválido no arquivo de input, linha {}: {}".format(idx, email))
                    sys.exit()

            MailServer("test_database", emails, 65000)