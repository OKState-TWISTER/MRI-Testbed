using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Thorlabs.MotionControl.Benchtop.StepperMotorCLI;
using Thorlabs.MotionControl.DeviceManagerCLI;
using Thorlabs.MotionControl.GenericMotorCLI;
using System.Threading;
using Thorlabs.MotionControl.GenericMotorCLI.ControlParameters;
using Thorlabs.MotionControl.GenericMotorCLI.AdvancedMotor;
using Thorlabs.MotionControl.GenericMotorCLI.Settings;

using Ivi.Visa;
using Ivi.Visa.FormattedIO;

namespace CharacterizeCLI
{
    internal class Program
    {
        static void Main(string[] args)
        {
            SimulationManager.Instance.InitializeSimulations();

            string serialNo = "40163084"; // rotation stage address
            string VISA_ADDRESS = "USB0::0x2A8D::0x9027::MY59190106::0::INSTR"; // DSO address
            

            int averagingTimeDelay = 5; // time in seconds to wait for RF power averaging

            int startingPos = 315; //the "home" position
            int endingPos = 315 - 90;
            MotorDirection rotateDirection = MotorDirection.Backward;


            //// Initalize Oscilloscope //////////////////////////////////////////////////////////////
            // Create a connection (session) to the instrument
            IMessageBasedSession session;
            try
            {
                session = GlobalResourceManager.Open(VISA_ADDRESS) as
                IMessageBasedSession;
            }
            catch (NativeVisaException visaException)
            {
                Console.WriteLine("Couldn't connect.");
                Console.WriteLine("Error is:\r\n{0}\r\n", visaException);
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
                return;
            }
            // Create a formatted I/O object which will help us format the
            // data we want to send/receive to/from the instrument
            MessageBasedFormattedIO myScope =
            new MessageBasedFormattedIO(session);
            // For Serial and TCP/IP socket connections enable the read
            // Termination Character, or read's will timeout
            if (session.ResourceName.Contains("ASRL") || session.ResourceName.Contains("SOCKET"))
                session.TerminationCharacterEnabled = true;
            session.TimeoutMilliseconds = 20000;
            // Initialize - start from a known state.
            // ==============================================================
            string strResults;
            FileStream fStream;
            // Clear status.
            myScope.WriteLine("*CLS");
            // Get and display the device's *IDN? string.
            myScope.WriteLine("*IDN?");
            strResults = myScope.ReadLine();
            Console.WriteLine("*IDN? result is: {0}", strResults);

            // Load saved setup #9
            myScope.WriteLine(":RECall:SETup 9");

            // Load setup file from computer executing code
            /*
            string setupFilePath = "E:\\VDI Characterization.set";
            byte[] DataArray;
            int nBytesWritten;
            // Read setup string from file.
            DataArray = File.ReadAllBytes(setupFilePath);
            nBytesWritten = DataArray.Length;
            // Restore setup string.
            myScope.Write(":SYSTem:SETup ");
            myScope.WriteBinary(DataArray);
            myScope.WriteLine("");
            Console.WriteLine("Setup bytes restored: {0}", nBytesWritten);
            */

            // Setup measuring
            // ==============================================================
            /*
            myScope.WriteLine(":FUNCtion3:FFT:PEAK:STATe ON");
            strResults = myScope.ReadLine();
            myScope.WriteLine(":FUNCtion3:FFT:PEAK:COUNt 1");
            strResults = myScope.ReadLine();
            */
            myScope.WriteLine(":FUNCtion3:FFT:PEAK:LEVel?");
            strResults = myScope.ReadLine();
            Console.WriteLine("Scope will measure RF peaks above {0}", strResults);




            //// Initialize rotation stage ////////////////////////////////////////////////////
            try
            {
                DeviceManagerCLI.BuildDeviceList();
            }
            catch (Exception ex)
            {
                Console.WriteLine("Exception raised by BuildDeviceList {0}", ex);
                Console.ReadKey();
                return;
            }
            BenchtopStepperMotor device = BenchtopStepperMotor.CreateBenchtopStepperMotor(serialNo);
            if (device == null)
            {
                Console.WriteLine("{0} is not a BenchtopStepperMotor", serialNo);
                Console.ReadKey();
                return;
            }
            try
            {
                Console.WriteLine("Opening device {0}", serialNo);
                device.Connect(serialNo);
            }
            catch (Exception)
            {
                Console.WriteLine("Failed to open device {0}", serialNo);
                Console.ReadKey();
                return;
            }
            StepperMotorChannel channel = device.GetChannel(1);
            if (channel == null)
            {
                Console.WriteLine("Channel unavailable {0}", serialNo);
                Console.ReadKey();
                return;
            }
            if (!channel.IsSettingsInitialized())
            {
                try
                {
                    channel.WaitForSettingsInitialized(5000);
                }
                catch (Exception)
                {
                    Console.WriteLine("Settings failed to initialize");
                }
            }
            // Start the device polling
            // The polling loop requests regular status requests to the motor to ensure the program keeps track of the device.
            channel.StartPolling(250);
            // Needs a delay so that the current enabled state can be obtained
            Thread.Sleep(500);
            // Enable the channel otherwise any move is ignored 
            channel.EnableDevice();
            // Needs a delay to give time for the device to be enabled
            Thread.Sleep(500);
            Console.WriteLine("Device Enabled");

            ////Initialize Oscilloscope



            //setup stage
            MotorConfiguration motorConfiguration = channel.LoadMotorConfiguration(channel.DeviceID);
            DeviceInfo deviceInfo = channel.GetDeviceInfo();
            Console.WriteLine("Device {0} = {1}", deviceInfo.SerialNumber, deviceInfo.Name);

            channel.SetBacklash(0);
            //channel.SetMovementSettings()


            ////Begin work
            Console.WriteLine("Actuator is Homing");
            channel.MoveTo(startingPos, 60000);

            Console.WriteLine("Stage is zeroed. Press any key to begin...");
            Console.ReadKey();

            // get position
            decimal angle = channel.DevicePosition;
            Console.WriteLine("current angle is: {0}", angle - startingPos);

            do
            {
                Console.WriteLine("Angle is {0} degrees", angle - startingPos);
                Thread.Sleep(5000);

                // record peak power value
                myScope.WriteLine(":FUNCtion3:FFT:PEAK:MAGNitude?");
                strResults = myScope.ReadLine();
                Console.WriteLine("Power level: {0}", strResults);

                //TODO: end test prematurely if "9.99e37" is returned (no peak value found)

                Console.WriteLine("Actuator is Moving");
                channel.MoveRelative(rotateDirection, 0.5m, 60000);
                angle = channel.DevicePosition;
            } while (angle > endingPos);

            Console.WriteLine("Angle is {0}", angle);

            //// Shutdown
            //stage
            channel.StopPolling();
            device.ShutDown();
            //scope
            session.Dispose();

            Console.WriteLine("Press any key to exit...");
            Console.ReadKey();
        }
    }
}
